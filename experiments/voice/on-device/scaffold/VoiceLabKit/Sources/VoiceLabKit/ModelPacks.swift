import Foundation

public struct ModelPackManifest: Codable, Sendable {
    public let id: String
    public let version: String
    public let task: VoiceTask
    public let backend: BackendType
    public let locale: String
    public let sizeBytes: Int64
    public let entrypoint: String

    enum CodingKeys: String, CodingKey {
        case id
        case version
        case task
        case backend
        case locale
        case sizeBytes = "size_bytes"
        case entrypoint
    }

    public init(
        id: String,
        version: String,
        task: VoiceTask,
        backend: BackendType,
        locale: String,
        sizeBytes: Int64,
        entrypoint: String
    ) {
        self.id = id
        self.version = version
        self.task = task
        self.backend = backend
        self.locale = locale
        self.sizeBytes = sizeBytes
        self.entrypoint = entrypoint
    }
}

public actor FileSystemModelPackManager: ModelPackManager {
    private let manifestsURL: URL
    private let decoder = JSONDecoder()

    public init(manifestsURL: URL) {
        self.manifestsURL = manifestsURL
    }

    public func isTaskAvailable(_ task: VoiceTask) async -> Bool {
        (try? loadManifests().contains(where: { $0.task == task })) ?? false
    }

    public func activeBackend(for task: VoiceTask) async -> BackendType? {
        try? loadManifests().first(where: { $0.task == task })?.backend
    }

    public func activeManifest(for task: VoiceTask, locale: String) async throws -> ModelPackManifest {
        let manifests = try loadManifests()
        if let exact = manifests.first(where: { $0.task == task && $0.locale == locale }) {
            return exact
        }
        if let fallback = manifests.first(where: { $0.task == task }) {
            return fallback
        }
        throw VoiceError(
            code: "MODEL_PACK_MISSING",
            message: "No active model pack for task \(task.rawValue).",
            details: "Expected manifests under \(manifestsURL.path)"
        )
    }

    private func loadManifests() throws -> [ModelPackManifest] {
        guard FileManager.default.fileExists(atPath: manifestsURL.path) else {
            return []
        }
        let data = try Data(contentsOf: manifestsURL)
        return try decoder.decode([ModelPackManifest].self, from: data)
    }
}

