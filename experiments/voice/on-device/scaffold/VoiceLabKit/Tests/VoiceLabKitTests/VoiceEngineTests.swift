import Foundation
import XCTest
@testable import VoiceLabKit

final class VoiceEngineTests: XCTestCase {
    func testHealthShowsAvailableTasks() async throws {
        let manager = InMemoryModelPackManager(taskBackends: [.tts: .coreml, .stt: .mlx])
        let outputDirectory = FileManager.default.temporaryDirectory
        let synth = MockSynthesisEngine(outputDirectory: outputDirectory)
        let stt = MockTranscriptionEngine()
        let engine = VoiceEngine(
            synthesisEngine: synth,
            transcriptionEngine: stt,
            modelPackManager: manager
        )

        let health = await engine.health()
        XCTAssertTrue(health.ok)
        XCTAssertTrue(health.availableTasks.contains(.tts))
        XCTAssertTrue(health.availableTasks.contains(.stt))
    }

    func testTTSFailsWhenPackMissing() async throws {
        let manager = InMemoryModelPackManager(taskBackends: [.stt: .mlx])
        let outputDirectory = FileManager.default.temporaryDirectory
        let synth = MockSynthesisEngine(outputDirectory: outputDirectory)
        let stt = MockTranscriptionEngine()
        let engine = VoiceEngine(
            synthesisEngine: synth,
            transcriptionEngine: stt,
            modelPackManager: manager
        )

        do {
            _ = try await engine.textToSpeech(TTSRequest(text: "hi", voice: "default", locale: "en-US"))
            XCTFail("Expected error when tts model pack is missing")
        } catch let error as VoiceError {
            XCTAssertEqual(error.code, "MODEL_PACK_MISSING")
        }
    }
}
