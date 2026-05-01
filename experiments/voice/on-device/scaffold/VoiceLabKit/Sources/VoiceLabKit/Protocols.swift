import Foundation

public protocol SynthesisEngine: Sendable {
    var backend: BackendType { get }
    func synthesize(_ request: TTSRequest) async throws -> TTSResponse
}

public protocol TranscriptionEngine: Sendable {
    var backend: BackendType { get }
    func transcribe(_ request: STTRequest) async throws -> STTResponse
}

public protocol ModelPackManager: Sendable {
    func isTaskAvailable(_ task: VoiceTask) async -> Bool
    func activeBackend(for task: VoiceTask) async -> BackendType?
}

