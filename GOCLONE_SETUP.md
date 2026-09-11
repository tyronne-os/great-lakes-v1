# Goclone in Podman - Setup Guide

## Project Overview
Goclone is a website cloner written in Go that uses goroutines to download websites efficiently. This setup allows you to run goclone in an isolated Podman container while keeping the source code available for study.

## Quick Start

### 1. Build the Podman Image
```bash
cd /home/hunt/Downloads/FOR\ SQL
podman build -t goclone:latest -f Dockerfile .
```

### 2. Run Goclone
Clone a website:
```bash
podman run --rm -v ./output:/output goclone:latest https://example.com
```

With specific options:
```bash
podman run --rm -v ./output:/output goclone:latest https://example.com --serve --servePort 5000
```

### Using Podman Compose

If you prefer docker-compose style commands:
```bash
# Build
podman-compose -f podman-compose.yml build

# Run
podman-compose -f podman-compose.yml run --rm goclone https://example.com
```

## Understanding the Dockerfile

The Dockerfile uses a **multi-stage build** for efficiency:

1. **Builder Stage** (golang:1.20-alpine):
   - Downloads Go dependencies from go.mod
   - Compiles the goclone source code to a binary
   - Creates `/goclone` executable

2. **Runtime Stage** (alpine:latest):
   - Lightweight base image (~5MB vs 300MB+)
   - Copies only the compiled binary from builder
   - Final image is small and production-ready

## Exploring the Source Code

The goclone source is already cloned in `/home/hunt/Downloads/FOR\ SQL/goclone/`:

```
goclone/
├── cmd/goclone/main.go        # Entry point
├── cmd/                         # Command logic
├── pkg/                         # Core packages (cloner, collector, etc.)
├── go.mod                       # Dependencies
└── README.md                    # Official documentation
```

Key files to study:
- `pkg/colly/` - Website scraping logic
- `pkg/core/` - Cloning algorithm
- `cmd/root.go` - CLI argument handling

## Common Usage Examples

### Clone a website to local directory
```bash
podman run --rm \
  -v ./output:/output \
  goclone:latest \
  https://configtree.co
```

### Clone and serve it locally
```bash
podman run --rm \
  -v ./output:/output \
  -p 5000:5000 \
  goclone:latest \
  https://example.com --serve --servePort 5000
```

### Using custom headers/cookies
```bash
podman run --rm \
  -v ./output:/output \
  goclone:latest \
  https://example.com \
  -u "Mozilla/5.0 (X11; Linux x86_64)" \
  -C "session_id=abc123"
```

### Using a proxy
```bash
podman run --rm \
  -v ./output:/output \
  goclone:latest \
  https://example.com \
  -p "http://proxy.example.com:8080"
```

## Goclone Flags Reference

- `-C, --cookie strings` - Set cookies for requests
- `-h, --help` - Show help
- `-o, --open` - Automatically open cloned site in browser
- `-p, --proxy_string` - Proxy URL (http or socks5)
- `-s, --serve` - Start a local web server for the cloned site
- `-P, --servePort int` - Port for the web server (default 5000)
- `-u, --user_agent` - Custom user agent string

## Directory Structure

```
/home/hunt/Downloads/FOR\ SQL/
├── goclone/                    # Cloned repository (source code)
├── Dockerfile                  # Container definition
├── podman-compose.yml          # Compose file
├── output/                     # Cloned websites saved here
└── GOCLONE_SETUP.md           # This file
```

## Next Steps for Learning

1. **Read the main entry point**: `goclone/cmd/goclone/main.go`
2. **Study CLI setup**: `goclone/cmd/root.go` and `goclone/cmd/*.go`
3. **Understand the cloning logic**: `goclone/pkg/core/`
4. **Explore web scraping**: `goclone/pkg/colly/`
5. **Check dependencies**: Review `go.mod` to see what libraries they use

## Troubleshooting

**Image build fails:**
```bash
# Check if Podman is running
podman info

# Force rebuild without cache
podman build --no-cache -t goclone:latest -f Dockerfile .
```

**Permission denied on volume:**
```bash
# Ensure output directory exists and is writable
mkdir -p ./output
chmod 777 ./output
```

**Container exits immediately:**
```bash
# Run with verbose output
podman run -it --rm -v ./output:/output goclone:latest --help
```

## Additional Resources

- Official goclone repo: https://github.com/tyronne-os/goclone
- Colly docs (web scraping): http://go-colly.org/
- Go documentation: https://golang.org/doc/
