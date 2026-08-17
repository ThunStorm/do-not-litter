import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
    fputs("usage: vision_ocr.swift <image>\n", stderr)
    exit(64)
}

let path = CommandLine.arguments[1]
guard
    let image = NSImage(contentsOfFile: path),
    let tiff = image.tiffRepresentation,
    let bitmap = NSBitmapImageRep(data: tiff),
    let cgImage = bitmap.cgImage
else {
    fputs("cannot decode image\n", stderr)
    exit(65)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
    let rows: [[String: Any]] = (request.results ?? []).compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return [
            "text": candidate.string,
            "confidence": candidate.confidence,
            "bbox": [box.origin.x, box.origin.y, box.size.width, box.size.height],
        ]
    }
    let data = try JSONSerialization.data(withJSONObject: rows, options: [])
    print(String(decoding: data, as: UTF8.self))
} catch {
    fputs("Vision OCR failed: \(error)\n", stderr)
    exit(70)
}
