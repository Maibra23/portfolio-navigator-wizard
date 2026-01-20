# Make Wrapper Script
# Ensures Make is in PATH before running make commands

$makePath = "C:\Program Files (x86)\GnuWin32\bin"

# Add Make to PATH if not already there
if ($env:Path -notlike "*$makePath*") {
    $env:Path += ";$makePath"
}

# Run make with all arguments passed to this script
& make $args
