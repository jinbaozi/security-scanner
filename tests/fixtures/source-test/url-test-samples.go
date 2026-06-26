package main

import (
	// 正常 Go import，应被白名单豁免。
	"fmt"
	"net/http"

	// Go 模块 import，应被白名单豁免。
	_ "github.com/gin-gonic/gin"
	_ "gitee.com/example/lib"
)

// 硬编码公网地址，应报告。
const APIEndpoint = "http://api.external-service.com/v1/data"
const BackupServer = "https://103.45.67.89:8443/backup"

// 硬编码邮箱，应报告。
const AdminEmail = "admin@external-company.com"

// 标准协议命名空间，应被白名单豁免。
const SOAPNamespace = "http://schemas.xmlsoap.org/soap/envelope/"
const W3CSchema = "http://www.w3.org/2001/XMLSchema"

// 内网地址硬编码，可作为信息项或人工确认项。
const InternalAPI = "http://10.20.30.40:8080/internal/api"

// 使用 HTTP 而非 HTTPS，应报告。
const InsecureEndpoint = "http://api.partner.com/data"

func main() {
	fmt.Println(APIEndpoint, BackupServer, AdminEmail, SOAPNamespace, W3CSchema, InternalAPI, InsecureEndpoint)
	http.ListenAndServe(":8080", nil)
}
