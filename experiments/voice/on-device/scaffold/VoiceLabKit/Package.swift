// swift-tools-version: 6.3
import PackageDescription

let package = Package(
    name: "VoiceLabKit",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(name: "VoiceLabKit", targets: ["VoiceLabKit"]),
        .executable(name: "VoiceLabCLI", targets: ["VoiceLabCLI"])
    ],
    targets: [
        .target(name: "VoiceLabKit"),
        .executableTarget(name: "VoiceLabCLI", dependencies: ["VoiceLabKit"]),
        .testTarget(name: "VoiceLabKitTests", dependencies: ["VoiceLabKit"])
    ]
)
