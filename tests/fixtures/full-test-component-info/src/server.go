package main

import (
    "crypto/md5"
    "crypto/tls"
    "net/http"
)

func main() {
    data := []byte("password")
    h := md5.Sum(data)  // crypto + secret dual-detect
    cfg := &tls.Config{MinVersion: tls.VersionTLS12}
    http.ListenAndServeTLS(":8443", "cert.pem", "key.pem", nil)  // network
    _ = h
    _ = cfg
}
