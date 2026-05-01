import Foundation

public struct CoreMLSynthesisEngine: SynthesisEngine {
    public let backend: BackendType = .coreml
    private let modelPackManager: FileSystemModelPackManager
    private let outputDirectory: URL

    public init(modelPackManager: FileSystemModelPackManager, outputDirectory: URL) {
        self.modelPackManager = modelPackManager
        self.outputDirectory = outputDirectory
    }

    public func synthesize(_ request: TTSRequest) async throws -> TTSResponse {
        let manifest = try await modelPackManager.activeManifest(for: .tts, locale: request.locale)
        guard manifest.backend == .coreml else {
            throw VoiceError(
                code: "BACKEND_UNAVAILABLE",
                message: "Active TTS pack is not a Core ML pack.",
                details: "Found backend \(manifest.backend.rawValue)"
            )
        }

        try FileManager.default.createDirectory(at: outputDirectory, withIntermediateDirectories: true)
        let outputURL = outputDirectory.appendingPathComponent("tts-output.wav")

        throw VoiceError(
            code: "INFERENCE_FAILED",
            message: "Core ML TTS adapter is not implemented yet.",
            details: "Wire a model adapter for entrypoint \(manifest.entrypoint). Expected output path: \(outputURL.path)"
        )
    }
}

public struct CoreMLTranscriptionEngine: TranscriptionEngine {
    public let backend: BackendType = .coreml
    private let modelPackManager: FileSystemModelPackManager

    public init(modelPackManager: FileSystemModelPackManager) {
        self.modelPackManager = modelPackManager
    }

    public func transcribe(_ request: STTRequest) async throws -> STTResponse {
        let manifest = try await modelPackManager.activeManifest(for: .stt, locale: request.locale)
        guard manifest.backend == .coreml else {
            throw VoiceError(
                code: "BACKEND_UNAVAILABLE",
                message: "Active STT pack is not a Core ML pack.",
                details: "Found backend \(manifest.backend.rawValue)"
            )
        }

        throw VoiceError(
            code: "INFERENCE_FAILED",
            message: "Core ML STT adapter is not implemented yet.",
            details: "Wire a model adapter for entrypoint \(manifest.entrypoint). Input audio: \(request.audioFileURL.path)"
        )
    }
}

