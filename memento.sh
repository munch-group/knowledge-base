#!/usr/bin/env bash


FILE="file:///Users/kmt/memento/memento.html"

osascript <<EOF
tell application "Google Chrome"
    set found to false
    repeat with w in windows
        set tabIndex to 0
        repeat with t in tabs of w
            set tabIndex to tabIndex + 1
            if URL of t is "$FILE" then
                set active tab index of w to tabIndex
                activate
                set found to true
                exit repeat
            end if
        end repeat
        if found then exit repeat
    end repeat
    if not found then
        if (count windows) = 0 then
            make new window
        end if
        tell front window to make new tab with properties {URL:"$FILE"}
        activate
    end if
end tell
EOF
