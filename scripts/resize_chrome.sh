#!/bin/bash

# Default Dimensions (User Custom Square)
WIDTH=${1:-850}
HEIGHT=${2:-850}

# AppleScript to resize Chrome
osascript -e "tell application \"Google Chrome\"
    if (count of windows) > 0 then
        set bounds of front window to {0, 0, $WIDTH, $HEIGHT}
        return \"Resized to \" & $WIDTH & \"x\" & $HEIGHT
    else
        return \"No Chrome window found\"
    end if
end tell"
