import Foundation

public struct InMemoryModelPackManager: ModelPackManager {
    private let taskBackends: [VoiceTask: BackendType]

    public init(taskBackends: [VoiceTask: BackendType]) {
        self.taskBackends = taskBackends
    }

    public func isTaskAvailable(_ task: VoiceTask) async -> Bool {
        taskBackends[task] != nil
    }

    public func activeBackend(for task: VoiceTask) async -> BackendType? {
        taskBackends[task]
    }
}

public struct MockSynthesisEngine: SynthesisEngine {
    public let backend: BackendType
    public let outputDirectory: URL

    public init(backend: BackendType = .mock, outputDirectory: URL) {
        self.backend = backend
        self.outputDirectory = outputDirectory
    }

    public func synthesize(_ request: TTSRequest) async throws -> TTSResponse {
        let fileURL = outputDirectory.appendingPathComponent("mock-tts.wav")
        try Data().write(to: fileURL)
        return TTSResponse(outputFileURL: fileURL, sampleRateHz: 24000, durationMs: max(500, request.text.count * 35))
    }
}

public struct MockTranscriptionEngine: TranscriptionEngine {
    public let backend: BackendType

    public init(backend: BackendType = .mock) {
        self.backend = backend
    }

    public func transcribe(_ request: STTRequest) async throws -> STTResponse {
        _ = request
        return STTResponse(text: "Mock transcription", durationMs: 1000)
    }
}

