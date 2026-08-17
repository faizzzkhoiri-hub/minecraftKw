# minecraftKw v1

Python/Pygame game project prepared for Android packaging with Buildozer.

## GitHub Actions

The workflow in `.github/workflows/build.yml` builds a debug APK and uploads it as an artifact named `minecraftKw-v1-apk`.

If the build fails, a `minecraftKw-v1-build-log` artifact is uploaded so the exact Buildozer error can be inspected.
