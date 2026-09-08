import type { MapMarker } from '../../lib/types'

function markerPixel(marker: MapMarker, zoom: number) {
  const size = 256 * 2 ** zoom
  const latitude = Math.min(85.051129, Math.max(-85.051129, marker.latitude)) * Math.PI / 180
  return {
    x: (marker.longitude + 180) / 360 * size,
    y: (0.5 - Math.log((1 + Math.sin(latitude)) / (1 - Math.sin(latitude))) / (4 * Math.PI)) * size,
  }
}

export function groupMarkersByPixel(markers: MapMarker[], zoom: number, threshold = 42) {
  const pixels = markers.map((marker) => markerPixel(marker, zoom))
  const parent = markers.map((_, index) => index)
  const find = (index: number): number => parent[index] === index ? index : (parent[index] = find(parent[index]))
  const union = (left: number, right: number) => {
    const leftRoot = find(left)
    const rightRoot = find(right)
    if (leftRoot !== rightRoot) parent[rightRoot] = leftRoot
  }
  const cells = new Map<string, number[]>()
  pixels.forEach((pixel, index) => {
    const cellX = Math.floor(pixel.x / threshold)
    const cellY = Math.floor(pixel.y / threshold)
    for (let x = cellX - 1; x <= cellX + 1; x += 1) {
      for (let y = cellY - 1; y <= cellY + 1; y += 1) {
        for (const other of cells.get(`${x}:${y}`) ?? []) {
          if (Math.hypot(pixel.x - pixels[other].x, pixel.y - pixels[other].y) < threshold) union(index, other)
        }
      }
    }
    const key = `${cellX}:${cellY}`
    cells.set(key, [...(cells.get(key) ?? []), index])
  })
  const groups = new Map<number, MapMarker[]>()
  markers.forEach((marker, index) => {
    const root = find(index)
    groups.set(root, [...(groups.get(root) ?? []), marker])
  })
  return [...groups.values()]
}
