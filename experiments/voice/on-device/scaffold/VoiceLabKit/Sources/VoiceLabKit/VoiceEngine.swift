import Foundation

public actor VoiceEngine {
    private let synthesisEngine: SynthesisEngine
    private let transcriptionEngine: TranscriptionEngine
    private let modelPackManager: ModelPackManager

    public init(
        synthesisEngine: SynthesisEngine,
        transcriptionEngine: TranscriptionEngine,
        modelPackManager: ModelPackManager
    ) {
        self.synthesisEngine = synthesisEngine
        self.transcriptionEngine = transcriptionEngine
        self.modelPackManager = modelPackManager
    }

    public func health() async -> HealthStatus {
        let ttsAvailable = await modelPackManager.isTaskAvailable(.tts)
        let sttAvailable = await modelPackManager.isTaskAvailable(.stt)
        let backend = await modelPackManager.activeBackend(for: .tts) ?? .mock
        let tasks: [VoiceTask] = [ttsAvailable ? .tts : nil, sttAvailable ? .stt : nil].compactMap { $0 }
        return HealthStatus(ok: ttsAvailable || sttAvailable, activeBackend: backend, availableTasks: tasks)
    }

    public func textToSpeech(_ request: TTSRequest) async throws -> TTSResponse {
        guard await modelPackManager.isTaskAvailable(.tts) else {
            throw VoiceError(
                code: "MODEL_PACK_MISSING",
                message: "No active model pack for task tts.",
                details: "Install a TTS model pack before running synthesis."
            )
        }
        return try await synthesisEngine.synthesize(request)
    }

    public func speechToText(_ request: STTRequest) async throws -> STTResponse {
        guard await modelPackManager.isTaskAvailable(.stt) else {
            throw VoiceError(
                code: "MODEL_PACK_MISSING",
                message: "No active model pack for task stt.",
                details: "Install an STT model pack before running transcription."
            )
        }
        return try await transcriptionEngine.transcribe(request)
    }
}

