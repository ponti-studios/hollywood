import Foundation
import VoiceLabKit

enum CLIMode: String {
    case mock
    case coreml
}

struct CLIOptions {
    var command: String
    var mode: CLIMode = .mock
    var text: String = "Hello from VoiceLabCLI."
    var voice: String = "default.en.us.female"
    var locale: String = "en-US"
    var inputAudioPath: String = ""
    var inputDirectoryPath: String = ""
    var outputDirPath: String = FileManager.default.temporaryDirectory.path
    var manifestsPath: String = ""
}

@main
struct VoiceLabCLIMain {
    static func main() async {
        do {
            let options = try parseArguments()
            try await run(options: options)
        } catch let error as VoiceError {
            fputs("[\(error.code)] \(error.message)\n", stderr)
            if let details = error.details {
                fputs("\(details)\n", stderr)
            }
            Foundation.exit(1)
        } catch {
            fputs("Unexpected error: \(error)\n", stderr)
            Foundation.exit(1)
        }
    }

    static func parseArguments() throws -> CLIOptions {
        var iterator = CommandLine.arguments.dropFirst().makeIterator()
        guard let command = iterator.next() else {
            throw VoiceError(code: "INVALID_REQUEST", message: "Missing command.", details: "Use one of: health, tts, stt, stt-batch")
        }

        var options = CLIOptions(command: command)
        while let arg = iterator.next() {
            switch arg {
            case "--mode":
                guard let value = iterator.next(), let parsed = CLIMode(rawValue: value) else {
                    throw VoiceError(code: "INVALID_REQUEST", message: "Invalid mode.", details: "Use mock or coreml")
                }
                options.mode = parsed
            case "--text":
                options.text = iterator.next() ?? options.text
            case "--voice":
                options.voice = iterator.next() ?? options.voice
            case "--locale":
                options.locale = iterator.next() ?? options.locale
            case "--input-audio":
                options.inputAudioPath = iterator.next() ?? ""
            case "--input-dir":
                options.inputDirectoryPath = iterator.next() ?? ""
            case "--output-dir":
                options.outputDirPath = iterator.next() ?? options.outputDirPath
            case "--manifests":
                options.manifestsPath = iterator.next() ?? ""
            default:
                throw VoiceError(code: "INVALID_REQUEST", message: "Unknown argument \(arg).")
            }
        }

        return options
    }

    static func run(options: CLIOptions) async throws {
        let outputDir = URL(fileURLWithPath: options.outputDirPath, isDirectory: true)
        try FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)

        let engine: VoiceEngine
        if options.mode == .mock {
            let manager = InMemoryModelPackManager(taskBackends: [.tts: .mock, .stt: .mock])
            let synth = MockSynthesisEngine(outputDirectory: outputDir)
            let stt = MockTranscriptionEngine()
            engine = VoiceEngine(synthesisEngine: synth, transcriptionEngine: stt, modelPackManager: manager)
        } else {
            guard !options.manifestsPath.isEmpty else {
                throw VoiceError(
                    code: "INVALID_REQUEST",
                    message: "Missing manifests path in coreml mode.",
                    details: "Pass --manifests /path/to/manifests.json"
                )
            }
            let manifestsURL = URL(fileURLWithPath: options.manifestsPath)
            let manager = FileSystemModelPackManager(manifestsURL: manifestsURL)
            let synth = CoreMLSynthesisEngine(modelPackManager: manager, outputDirectory: outputDir)
            let stt = CoreMLTranscriptionEngine(modelPackManager: manager)
            engine = VoiceEngine(synthesisEngine: synth, transcriptionEngine: stt, modelPackManager: manager)
        }

        switch options.command {
        case "health":
            let health = await engine.health()
            print("ok=\(health.ok) backend=\(health.activeBackend.rawValue) tasks=\(health.availableTasks.map { $0.rawValue }.joined(separator: ","))")
        case "tts":
            let result = try await engine.textToSpeech(TTSRequest(text: options.text, voice: options.voice, locale: options.locale))
            print("output=\(result.outputFileURL.path) sample_rate_hz=\(result.sampleRateHz) duration_ms=\(result.durationMs)")
        case "stt":
            guard !options.inputAudioPath.isEmpty else {
                throw VoiceError(
                    code: "INVALID_REQUEST",
                    message: "Missing input audio path.",
                    details: "Pass --input-audio /path/to/audio.wav"
                )
            }
            let inputURL = URL(fileURLWithPath: options.inputAudioPath)
            let result = try await engine.speechToText(STTRequest(audioFileURL: inputURL, locale: options.locale))
            print("text=\(result.text)\nduration_ms=\(result.durationMs)")
        case "stt-batch":
            guard !options.inputDirectoryPath.isEmpty else {
                throw VoiceError(
                    code: "INVALID_REQUEST",
                    message: "Missing input directory path.",
                    details: "Pass --input-dir /path/to/audio-folder"
                )
            }
            let inputDirectory = URL(fileURLWithPath: options.inputDirectoryPath, isDirectory: true)
            try await transcribeDirectory(
                engine: engine,
                inputDirectory: inputDirectory,
                locale: options.locale,
                outputDirectory: outputDir
            )
        default:
            throw VoiceError(code: "INVALID_REQUEST", message: "Unknown command \(options.command).", details: "Use health, tts, stt, or stt-batch")
        }
    }

    static func transcribeDirectory(
        engine: VoiceEngine,
        inputDirectory: URL,
        locale: String,
        outputDirectory: URL
    ) async throws {
        let fileManager = FileManager.default
        let audioURLs = try collectAudioFiles(in: inputDirectory)
        guard !audioURLs.isEmpty else {
            throw VoiceError(
                code: "INVALID_REQUEST",
                message: "No audio files found.",
                details: "Expected supported audio files under \(inputDirectory.path)"
            )
        }

        let transcriptDirectory = outputDirectory.appendingPathComponent("stt-transcripts", isDirectory: true)
        try fileManager.createDirectory(at: transcriptDirectory, withIntermediateDirectories: true)

        for audioURL in audioURLs {
            let result = try await engine.speechToText(STTRequest(audioFileURL: audioURL, locale: locale))
            let relativeTranscriptPath = transcriptPath(for: audioURL, rootedAt: inputDirectory)
            let transcriptURL = transcriptDirectory.appendingPathComponent(relativeTranscriptPath)
            try fileManager.createDirectory(at: transcriptURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try result.text.appending("\n").write(to: transcriptURL, atomically: true, encoding: .utf8)
            print("file=\(audioURL.lastPathComponent) transcript=\(transcriptURL.path) duration_ms=\(result.durationMs)")
        }
    }

    static func collectAudioFiles(in directory: URL) throws -> [URL] {
        let fileManager = FileManager.default
        let supportedExtensions: Set<String> = [
            "wav", "wave", "aiff", "aif", "caf", "m4a", "mp3", "aac", "mp4", "m4v", "flac"
        ]

        guard let enumerator = fileManager.enumerator(
            at: directory,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var audioFiles: [URL] = []
        for case let url as URL in enumerator {
            let isRegularFile = (try? url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) ?? false
            guard isRegularFile, supportedExtensions.contains(url.pathExtension.lowercased()) else {
                continue
            }
            audioFiles.append(url)
        }

        return audioFiles.sorted { $0.path.localizedStandardCompare($1.path) == .orderedAscending }
    }

    static func transcriptPath(for audioURL: URL, rootedAt rootDirectory: URL) -> String {
        let relativePath = audioURL.path.replacingOccurrences(
            of: rootDirectory.standardizedFileURL.path + "/",
            with: ""
        )
        let transcriptRelativePath = URL(fileURLWithPath: relativePath)
            .deletingPathExtension()
            .appendingPathExtension("txt")
            .path
        return transcriptRelativePath
    }
}
