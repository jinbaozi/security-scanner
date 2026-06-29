package main

import (
	"crypto/tls"
	"net/http"
)

func main() {
	cfg := &tls.Config{MinVersion: tls.VersionSSL30}  // RL-100: SSLv3
	server := &http.Server{Addr: ":8080", TLSConfig: cfg}  // Network-scanner
	server.ListenAndServeTLS("cert.pem", "key.pem")
}
