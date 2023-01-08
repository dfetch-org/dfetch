#!/bin/bash

# Check if a file path was provided as the first argument
if [ -z "$1" ]; then
    echo "Error: No file path provided"
    exit 1
fi

# Read the asciicast file into a variable
asciicast=$(<"$1")

# Find the line containing the escape sequence for clearing the screen
line=$(echo "$asciicast" | grep -n '\\u001b\[H\\u001b\[2J\\u001b\[3J' | cut -d: -f1)

# Check if a matching line was found
if [ -z "$line" ]; then
    echo "Warning: No line containing the escape sequence for clearing the screen was found"
else
    echo "Will remove lines 2 --> $line"
    # Remove all the lines before the line containing the escape sequence
    asciicast=$(echo "$asciicast" | sed -n "2,$((line-1))!p")

    # Write the updated asciicast to the file
    echo "$asciicast" > "$1"

fi
