/**
 * CctvLayer.ts — Public surveillance camera icon overlays on the 3D globe.
 *
 * Fetches the camera catalog from /api/live/cctv/cameras and places
 * billboard icons at each camera's geographic position on the terrain.
 * Clicking a camera fires the onCameraClick callback to open the pop-up.
 */

import * as Cesium from "cesium";

interface CctvCamera {
  id: string;
  name: string;
  imageUrl: string;
  agency: string;
  latitude: number;
  longitude: number;
}

function buildCctvCanvas(): HTMLCanvasElement {
  const size = 22;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#00ff9d";
  ctx.shadowColor = "#00ff9d";
  ctx.shadowBlur = 8;

  // Camera body
  ctx.fillRect(3, 6, 12, 9);
  // Lens circle
  ctx.beginPath();
  ctx.arc(9, 10, 3.5, 0, Math.PI * 2);
  ctx.fillStyle = "#070b12";
  ctx.fill();
  ctx.strokeStyle = "#00ff9d";
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Viewfinder triangle
  ctx.fillStyle = "#00ff9d";
  ctx.beginPath();
  ctx.moveTo(15, 7);
  ctx.lineTo(20, 5);
  ctx.lineTo(20, 15);
  ctx.lineTo(15, 13);
  ctx.closePath();
  ctx.fill();

  return canvas;
}

export class CctvLayer {
  private viewer: Cesium.Viewer;
  private billboards: Cesium.BillboardCollection;
  private cameras: CctvCamera[] = [];
  private visible = true;
  private onCameraClick: (cam: CctvCamera) => void;

  constructor(viewer: Cesium.Viewer, onCameraClick: (cam: CctvCamera) => void) {
    this.viewer = viewer;
    this.onCameraClick = onCameraClick;
    this.billboards = viewer.scene.primitives.add(
      new Cesium.BillboardCollection({ scene: viewer.scene })
    );

    this.fetchCameras();

    viewer.screenSpaceEventHandler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
      const picked = viewer.scene.pick(click.position);
      if (picked?.id?.startsWith?.("cctv:")) {
        const camId = picked.id.replace("cctv:", "");
        const cam = this.cameras.find((c) => c.id === camId);
        if (cam) this.onCameraClick(cam);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  }

  private async fetchCameras() {
    try {
      const resp = await fetch("/api/live/cctv/cameras");
      if (!resp.ok) return;
      const data = await resp.json();
      this.cameras = data.cameras ?? [];
      const icon = buildCctvCanvas();

      for (const cam of this.cameras) {
        this.billboards.add({
          position: Cesium.Cartesian3.fromDegrees(cam.longitude, cam.latitude, 50),
          image: icon,
          id: `cctv:${cam.id}`,
          width: 20,
          height: 20,
          show: this.visible,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        });
      }
    } catch (_) {}
  }

  setVisible(visible: boolean) {
    this.visible = visible;
    this.billboards.show = visible;
  }

  destroy() {
    this.viewer.scene.primitives.remove(this.billboards);
  }
}
