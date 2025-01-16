#!/bin/bash

# Navigate to the Git repository
cd /usr/share/rpi-metrics

# Get the latest commit information
commit_id=$(git log -1 --format="%H")
commit_time=$(git log -1 --format="%cd")

# Create a file to store the commit information
echo "Commit ID: $commit_id" > /usr/share/rpi-metrics/commit_info.txt
echo "Commit Time: $commit_time" >> /usr/share/rpi-metrics/commit_info.txt