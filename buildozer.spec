[app]

title = minecraftKw v1
package.name = minecraftkw
package.domain = com.minecraftkw

source.dir = .
source.include_exts = py,png,jpg,jpeg,wav,ogg,json,ttf

source.exclude_dirs = .git,.github,bin,.buildozer,saves

version = 1.0.0

requirements = python3==3.11.9,pygame

orientation = landscape
fullscreen = 1

android.api = 34
android.minapi = 23
android.ndk = 25b
android.ndk_api = 23

android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True
android.allow_backup = True

android.permissions = INTERNET

[buildozer]

log_level = 2
warn_on_root = 1
