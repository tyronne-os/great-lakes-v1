# Build stage
FROM docker.io/golang:1.25-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git make ca-certificates

# Set working directory
WORKDIR /app

# Copy go mod files
COPY goclone/go.mod goclone/go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY goclone/ .

# Build the binary
RUN go build -o /goclone cmd/goclone/main.go

# Runtime stage
FROM docker.io/alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates

# Create app directory and output directory
RUN mkdir -p /app /output

WORKDIR /app

# Copy binary from builder
COPY --from=builder /goclone /usr/local/bin/goclone

# Default command
ENTRYPOINT ["/usr/local/bin/goclone"]
CMD ["--help"]
