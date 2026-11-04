/**
 * WeatherRadarLayer.ts — NOAA nowCOAST MRMS Base Reflectivity WMS overlay.
 *
 * Fetches the radar WMS configuration from /api/live/weather/radar-wms
 * and adds the layer as a WebMapServiceImageryProvider at 0.65 alpha.
 */

import * as Cesium from "cesium";

export class WeatherRadarLayer {
  private viewer: Cesium.Viewer;
  private layer: Cesium.ImageryLayer | null = null;
  private visible = true;

  constructor(viewer: Cesium.Viewer) {
    this.viewer = viewer;
    this.init();
  }

  private async init() {
    try {
      const resp = await fetch("/api/live/weather/radar-wms");
      if (!resp.ok) return;
      const config = await resp.json();

      const provider = new Cesium.WebMapServiceImageryProvider({
        url: config.url,
        layers: config.layers,
        parameters: {
          transparent: true,
          format: "image/png",
          SERVICE: "WMS",
          VERSION: "1.3.0",
          REQUEST: "GetMap",
        },
        tilingScheme: new Cesium.WebMercatorTilingScheme(),
        maximumLevel: 6,
      });

      this.layer = this.viewer.imageryLayers.addImageryProvider(provider);
      this.layer.alpha = 0.65;
      this.layer.show = this.visible;
    } catch (_) {
      // Weather radar overlay is optional — silently fail
    }
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    if (this.layer) this.layer.show = visible;
  }

  destroy() {
    if (this.layer) {
      this.viewer.imageryLayers.remove(this.layer, true);
    }
  }
}
