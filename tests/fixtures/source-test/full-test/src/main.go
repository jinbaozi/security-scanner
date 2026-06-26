package main

import (
	"fmt"

	"github.com/gin-gonic/gin"
)

// 硬编码公网地址
const API_URL = "http://api.external.com/v1/data"
const DB_HOST = "203.0.113.50"

// 硬编码密码
const DB_PASSWORD = "secret_password_123"
const API_KEY = "sk-live-abc123"

func main() {
	r := gin.Default()
	r.GET("/ping", func(c *gin.Context) {
		c.JSON(200, gin.H{"message": "pong"})
	})
	fmt.Println(API_URL, DB_HOST, DB_PASSWORD, API_KEY)
	r.Run()
}
