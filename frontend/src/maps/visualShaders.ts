/**
 * visualShaders.ts
 * ────────────────────────────────────────────────────────────────────────────
 * Bridges the God's Eye View GLSL visual-preset shaders into the Cesium
 * PostProcessStageCollection.  Each VisualStyle maps to one PostProcessStage
 * that is enabled/disabled via setActiveStyle().
 *
 * Styles:
 *   1 – normal       (pass-through, no stage)
 *   2 – retro        (CRT scanlines, barrel distortion, dithering)
 *   3 – surveillance (NVG / night-vision green P43 phosphor)
 *   4 – thermal      (FLIR Ironbow thermal imaging)
 *   5 – anime        (ink outline + cel shading)
 *   6 – noir         (greyscale high-contrast film grain)
 *   7 – snow         (white-out blizzard particle overlay)
 */

import * as Cesium from 'cesium';
import type { VisualStyle } from './CesiumGlobe';

/* ── Inline GLSL ─────────────────────────────────────────────────────────── */

const retroGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

float hash2(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float bayer8(vec2 pos) {
  ivec2 p = ivec2(mod(pos, 8.0));
  int idx = p.x + p.y * 8;
  int b[64] = int[64](0,32,8,40,2,34,10,42,48,16,56,24,50,18,58,26,12,44,4,36,14,46,6,38,60,28,52,20,62,30,54,22,3,35,11,43,1,33,9,41,51,19,59,27,49,17,57,25,15,47,7,39,13,45,5,37,63,31,55,23,61,29,53,21);
  return float(b[idx]) / 64.0;
}
void main() {
  vec2 uv = v_textureCoordinates;
  vec2 dims = colorTextureDimensions;
  vec2 c = uv * 2.0 - 1.0;
  float r2 = dot(c, c);
  c *= 1.0 + r2 * 0.15;
  vec2 duv = c * 0.5 + 0.5;
  if (duv.x < 0.0 || duv.x > 1.0 || duv.y < 0.0 || duv.y > 1.0) {
    out_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return;
  }
  float lineY = floor(duv.y * dims.y);
  float jit = (hash2(vec2(lineY, czm_frameNumber)) - 0.5) * 0.003;
  vec2 juv = duv + vec2(jit, 0.0);
  vec2 cen = juv - 0.5;
  float ca = length(cen) * 0.006;
  float r = texture(colorTexture, juv + cen * ca).r;
  float g = texture(colorTexture, juv).g;
  float b = texture(colorTexture, juv - cen * ca).b;
  vec4 col = vec4(r, g, b, 1.0);
  float scanline = sin(duv.y * dims.y * 1.0 + czm_frameNumber * 0.15) * 0.5 + 0.5;
  col.rgb *= 0.7 + 0.3 * scanline;
  vec2 viguv = duv * (1.0 - duv);
  float vig = pow(viguv.x * viguv.y * 20.0, 0.35);
  col.rgb *= mix(0.5, 1.0, vig);
  float dth = bayer8(juv * dims / 4.0) - 0.5;
  col.rgb += dth * 0.06;
  col.rgb *= vec3(1.02, 1.0, 0.93);
  out_FragColor = col;
}`;

const nvgGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

float hash2(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
void main() {
  vec2 uv = v_textureCoordinates;
  vec2 dims = colorTextureDimensions;
  vec4 c = texture(colorTexture, uv);
  float lum = dot(c.rgb, vec3(0.299, 0.587, 0.114));
  float boosted = pow(lum * 1.6, 0.75);
  float noise = hash2(uv * dims + czm_frameNumber) * 0.07;
  boosted = clamp(boosted + noise, 0.0, 1.0);
  vec2 cen = uv - 0.5;
  float vig = 1.0 - smoothstep(0.3, 0.75, length(cen));
  boosted *= vig;
  float scan = sin(uv.y * dims.y * 1.0) * 0.5 + 0.5;
  boosted *= 0.88 + 0.12 * scan;
  out_FragColor = vec4(0.0, boosted, boosted * 0.18, 1.0);
}`;

const thermalGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

float hash2(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
vec3 ironbow(float t) {
  t = clamp(t, 0.0, 1.0);
  return vec3(
    clamp(4.0 * t - 1.5, 0.0, 1.0),
    clamp(sin(t * 3.14159), 0.0, 1.0),
    clamp(1.5 - 4.0 * t, 0.0, 1.0)
  );
}
void main() {
  vec2 uv = v_textureCoordinates;
  vec4 c = texture(colorTexture, uv);
  float lum = dot(c.rgb, vec3(0.299, 0.587, 0.114));
  float thermal = pow(lum, 0.6) * 1.2;
  float noise = hash2(uv * colorTextureDimensions + czm_frameNumber) * 0.03;
  thermal = clamp(thermal + noise, 0.0, 1.0);
  out_FragColor = vec4(ironbow(thermal), 1.0);
}`;

const animeGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

void main() {
  vec2 uv = v_textureCoordinates;
  vec2 texel = 1.0 / colorTextureDimensions;
  vec4 col = texture(colorTexture, uv);
  vec3 s00 = texture(colorTexture, uv + vec2(-texel.x,-texel.y)).rgb;
  vec3 s10 = texture(colorTexture, uv + vec2(0.0,-texel.y)).rgb;
  vec3 s20 = texture(colorTexture, uv + vec2(texel.x,-texel.y)).rgb;
  vec3 s01 = texture(colorTexture, uv + vec2(-texel.x,0.0)).rgb;
  vec3 s21 = texture(colorTexture, uv + vec2(texel.x,0.0)).rgb;
  vec3 s02 = texture(colorTexture, uv + vec2(-texel.x,texel.y)).rgb;
  vec3 s12 = texture(colorTexture, uv + vec2(0.0,texel.y)).rgb;
  vec3 s22 = texture(colorTexture, uv + vec2(texel.x,texel.y)).rgb;
  vec3 gx = -s00-2.0*s01-s02+s20+2.0*s21+s22;
  vec3 gy = -s00-2.0*s10-s20+s02+2.0*s12+s22;
  float edge = length(sqrt(gx*gx+gy*gy));
  float lum = dot(col.rgb,vec3(0.299,0.587,0.114));
  float cel = floor(lum*4.0)/4.0;
  vec3 celColor = col.rgb*(cel/max(lum,0.001));
  float gray = dot(celColor,vec3(0.299,0.587,0.114));
  celColor = mix(vec3(gray),celColor,1.6);
  float ink = 1.0-smoothstep(0.3,0.7,edge);
  out_FragColor = vec4(celColor*ink,1.0);
}`;

const noirGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

float hash2(vec2 p) {
  return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);
}
void main() {
  vec2 uv = v_textureCoordinates;
  vec4 c = texture(colorTexture,uv);
  float lum = dot(c.rgb,vec3(0.299,0.587,0.114));
  lum = smoothstep(0.15,0.85,lum);
  lum = pow(lum,1.3);
  float grain = hash2(uv*colorTextureDimensions+czm_frameNumber)*0.08-0.04;
  lum = clamp(lum+grain,0.0,1.0);
  vec2 cen = uv-0.5;
  float vig = 1.0-dot(cen,cen)*2.2;
  lum *= clamp(vig,0.0,1.0);
  out_FragColor = vec4(vec3(lum),1.0);
}`;

const snowGLSL = /* glsl */`
uniform sampler2D colorTexture;
uniform vec2 colorTextureDimensions;
in vec2 v_textureCoordinates;

float hash2(vec2 p) {
  return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);
}
void main() {
  vec2 uv = v_textureCoordinates;
  vec4 c = texture(colorTexture,uv);
  float lum = dot(c.rgb,vec3(0.299,0.587,0.114));
  vec3 cold = mix(c.rgb,vec3(lum),0.5);
  cold = mix(cold,vec3(1.0),0.25);
  vec2 st = uv*colorTextureDimensions/4.0;
  float t = czm_frameNumber*0.5;
  float snow = 0.0;
  for(int i=0;i<6;i++){
    vec2 offs = vec2(float(i)*47.3,float(i)*31.7);
    vec2 gv = fract(st*(0.5+float(i)*0.1)+vec2(t*0.01,t*0.04*(1.0+float(i)*0.1))+offs);
    float d = length(gv-0.5);
    snow += smoothstep(0.07,0.0,d)*(0.4+0.6*hash2(offs+floor(st)));
  }
  cold += clamp(snow,0.0,1.0)*0.9;
  out_FragColor = vec4(cold,1.0);
}`;

/* ── PostProcessStage registry ───────────────────────────────────────────── */

type ShaderKey = Exclude<VisualStyle, 'normal'>;

const SHADER_SOURCES: Record<ShaderKey, string> = {
  retro:        retroGLSL,
  surveillance: nvgGLSL,
  thermal:      thermalGLSL,
  anime:        animeGLSL,
  noir:         noirGLSL,
  snow:         snowGLSL,
};

export class VisualShaderManager {
  private _viewer: Cesium.Viewer;
  private _stages: Partial<Record<ShaderKey, Cesium.PostProcessStage>> = {};
  private _active: VisualStyle = 'normal';

  constructor(viewer: Cesium.Viewer) {
    this._viewer = viewer;
    this._buildStages();
  }

  private _buildStages() {
    const coll = this._viewer.scene.postProcessStages;
    for (const [key, glsl] of Object.entries(SHADER_SOURCES) as [ShaderKey, string][]) {
      try {
        const stage = new Cesium.PostProcessStage({
          name:           `gods_eye_${key}`,
          fragmentShader: glsl,
        });
        stage.enabled = false;
        coll.add(stage);
        this._stages[key] = stage;
      } catch (err) {
        console.warn(`[VisualShaderManager] Failed to compile shader "${key}":`, err);
      }
    }
  }

  setStyle(style: VisualStyle) {
    if (style === this._active) return;
    this._active = style;
    for (const [key, stage] of Object.entries(this._stages) as [ShaderKey, Cesium.PostProcessStage][]) {
      if (stage) stage.enabled = (key === style);
    }
  }

  getActive(): VisualStyle { return this._active; }

  destroy() {
    const coll = this._viewer.scene.postProcessStages;
    for (const stage of Object.values(this._stages)) {
      if (stage && !stage.isDestroyed()) {
        try { coll.remove(stage); } catch (_) {}
      }
    }
    this._stages = {};
  }
}
