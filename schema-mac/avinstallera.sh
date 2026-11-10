#!/bin/bash
# Tar bort den veckovisa körningen från din Mac.
LABEL="se.riskhantering.veckouppdatering"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
echo "Borttaget."
