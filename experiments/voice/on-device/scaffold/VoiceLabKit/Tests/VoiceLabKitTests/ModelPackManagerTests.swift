import Foundation
import XCTest
@testable import VoiceLabKit

final class ModelPackManagerTests: XCTestCase {
    func testLoadsTaskAvailabilityFromManifestFile() async throws {
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        let manifestURL = tempDir.appendingPathComponent("manifests.json")

        let manifests: [ModelPackManifest] = [
            ModelPackManifest(
                id: "tts-pack",
                version: "0.1.0",
                task: .tts,
                backend: .coreml,
                locale: "en-US",
                sizeBytes: 100,
                entrypoint: "tts/model.mlpackage"
            )
        ]
        let data = try JSONEncoder().encode(manifests)
        try data.write(to: manifestURL)

        let manager = FileSystemModelPackManager(manifestsURL: manifestURL)
        let ttsAvailable = await manager.isTaskAvailable(.tts)
        let sttAvailable = await manager.isTaskAvailable(.stt)
        let ttsBackend = await manager.activeBackend(for: .tts)

        XCTAssertTrue(ttsAvailable)
        XCTAssertFalse(sttAvailable)
        XCTAssertEqual(ttsBackend, .coreml)
    }
}

