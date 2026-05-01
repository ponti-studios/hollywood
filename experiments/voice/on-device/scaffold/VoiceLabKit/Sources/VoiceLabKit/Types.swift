import Foundation

public enum BackendType: String, Codable, Sendable {
    case coreml
    case mlx
    case mock
}

public enum VoiceTask: String, Codable, Sendable {
    case tts
    case stt
}

public struct VoiceError: Error, Sendable {
    public let code: String
    public let message: String
    public let details: String?

    public init(code: String, message: String, details: String? = nil) {
        self.code = code
        self.message = message
        self.details = details
    }
}

public struct TTSRequest: Sendable {
    public let text: String
    public let voice: String
    public let locale: String

    public init(text: String, voice: String, locale: String) {
        self.text = text
        self.voice = voice
        self.locale = locale
    }
}

public struct TTSResponse: Sendable {
    public let outputFileURL: URL
    public let sampleRateHz: Int
    public let durationMs: Int

    public init(outputFileURL: URL, sampleRateHz: Int, durationMs: Int) {
        self.outputFileURL = outputFileURL
        self.sampleRateHz = sampleRateHz
        self.durationMs = durationMs
    }
}

public struct STTRequest: Sendable {
    public let audioFileURL: URL
    public let locale: String

    public init(audioFileURL: URL, locale: String) {
        self.audioFileURL = audioFileURL
        self.locale = locale
    }
}

public struct STTResponse: Sendable {
    public let text: String
    public let durationMs: Int

    public init(text: String, durationMs: Int) {
        self.text = text
        self.durationMs = durationMs
    }
}

public struct HealthStatus: Sendable {
    public let ok: Bool
    public let activeBackend: BackendType
    public let availableTasks: [VoiceTask]

    public init(ok: Bool, activeBackend: BackendType, availableTasks: [VoiceTask]) {
        self.ok = ok
        self.activeBackend = activeBackend
        self.availableTasks = availableTasks
    }
}
