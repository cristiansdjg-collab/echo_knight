[app]
title = Echo Knight
package.name = echoknight
package.domain = org.echoknight
source.dir = .
source.include_exts = py,png
version = 11.2
requirements = python3,pygame
orientation = landscape
fullscreen = 1
icon.filename = Soult_icon.png

android.permissions =
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = master
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
