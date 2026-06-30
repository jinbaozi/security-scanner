# 架构类型推断信号库

> 本文件集中维护软件架构类型（B/S、C/S、嵌入式/单机服务等）推断所需的 pattern 集合。component-info-scanner 引用此文件。

## 1. 架构分类总览

| 架构类型 | 典型形态 | severity | 说明 |
|----------|---------|---------|------|
| B/S（Web 应用） | Django / Flask / FastAPI / Spring / Express / Gin / Laravel / Rails | info | 浏览器-服务器模式 |
| C/S（桌面 GUI） | Qt / GTK / Swing / JavaFX / Electron / Tkinter / wxWidgets | info | 客户端-服务器模式 |
| 嵌入式/单机服务 | 裸 socket / daemon / Telnet 服务 | info | 无 UI 或命令行服务 |
| unknown | 无明确信号 | info | 需人工确认 |

所有架构类型的 finding 输出 `severity=info`、`status=PASS`（仅做信息记录），除非人工 flag。

## 2. B/S 架构（Web 框架）

### 2.1 Python 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Django | `django\.(db\|http\|urls\|views\|models)` | `from django.db import models` |
| Flask | `flask\.Flask\|Flask\(__name__\)` | `app = Flask(__name__)` |
| FastAPI | `fastapi\.FastAPI\|FastAPI\(\)` | `app = FastAPI()` |

### 2.2 Java 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Spring Boot | `org\.springframework\|SpringApplication\|@SpringBootApplication` | `@SpringBootApplication` |
| Spring MVC | `@Controller\|@RestController\|@RequestMapping` | `@RestController` |

### 2.3 JavaScript / TypeScript 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Express | `express\(\)\|require\(['"]express['"]\)` | `const app = express()` |
| Koa | `require\(['"]koa['"]\)` | `const Koa = require('koa')` |
| NestJS | `@nestjs/(core\|common)` | `@nestjs/core` |

### 2.4 Go 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Gin | `gin\.Default\|gin\.Engine\|github.com/gin-gonic/gin` | `gin.Default()` |
| Echo | `echo\.New\|github.com/labstack/echo` | `e := echo.New()` |
| Beego | `github.com/beego/beego\|beego\.Run` | `beego.Run()` |

### 2.5 PHP 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Laravel | `Illuminate\\\|use Laravel\|laravel/framework` | `use Illuminate\Http\Request` |
| Symfony | `Symfony\\\|symfony/framework-bundle` | `use Symfony\Component` |
| ThinkPHP | `ThinkPHP\|think\\app` | `namespace app\index\controller` |

### 2.6 Ruby 框架

| 框架 | Pattern | 示例 |
|------|---------|------|
| Rails | `Rails\.application\|require ['"]rails['"]\|ActionController::Base` | `Rails.application.routes` |
| Sinatra | `require ['"]sinatra['"]\|Sinatra::Base` | `require 'sinatra'` |

## 3. C/S 架构（桌面 GUI）

### 3.1 Python GUI

| 库 | Pattern | 示例 |
|----|---------|------|
| Tkinter | `import\s+tkinter\|from\s+tkinter` | `from tkinter import Tk` |
| wxPython | `import\s+wx\|from\s+wx` | `import wx` |
| PyQt | `from\s+PyQt\|PyQt5\|PySide` | `from PyQt5 import QtWidgets` |
| Kivy | `import\s+kivy\|from\s+kivy` | `from kivy.app import App` |

### 3.2 Java GUI

| 库 | Pattern | 示例 |
|----|---------|------|
| Swing | `import\s+javax\.swing\|import\s+java\.awt` | `import javax.swing.JFrame` |
| JavaFX | `import\s+javafx` | `import javafx.application.Application` |
| SWT | `import\s+org\.eclipse\.swt` | `import org.eclipse.swt.widgets.Display` |

### 3.3 C/C++ GUI

| 库 | Pattern | 示例 |
|----|---------|------|
| Qt | `QMainWindow\|QWidget\|QApplication\|#include\s*<Q[^>]+>` | `#include <QMainWindow>` |
| GTK | `gtk_init\|gtk_window_new\|#include\s*<gtk/gtk\.h>` | `gtk_init(&argc, &argv)` |
| FLTK | `#include\s*<FL/Fl\.h>\|Fl_Window` | `Fl_Window window(300, 200)` |

### 3.4 C# / .NET GUI

| 库 | Pattern | 示例 |
|----|---------|------|
| WinForms | `using\s+System\.Windows\.Forms\|System\.Windows\.Forms\.Application` | `using System.Windows.Forms;` |
| WPF | `using\s+System\.Windows\|System.Windows.Application` | `using System.Windows;` |

### 3.5 跨平台 / Web-as-Desktop

| 库 | Pattern | 示例 |
|----|---------|------|
| Electron | `electron\|BrowserWindow\|require\(['"]electron['"]\)` | `const { app, BrowserWindow } = require('electron')` |
| Tauri | `tauri\|@tauri-apps/api` | `use tauri::Manager` |
| Flutter Desktop | `import\s+'package:flutter/material\.dart'` | `import 'package:flutter/material.dart'` |

## 4. 嵌入式 / 单机服务（裸 socket / daemon）

### 4.1 Python

| 模式 | Pattern | 示例 |
|------|---------|------|
| 裸 socket | `import\s+socket\|socket\.socket\(\)` | `sock = socket.socket()` |
| Telnet 库 | `telnetlib\.\|from\s+telnetlib` | `import telnetlib` |
| 多进程守护 | `multiprocessing\.Process\|setDaemon` | `multiprocessing.Process(target=...)` |

### 4.2 C/C++

| 模式 | Pattern | 示例 |
|------|---------|------|
| 裸 socket | `socket\(\s*AF_INET\|bind\(\s*sockfd\|listen\(\s*sockfd` | `socket(AF_INET, SOCK_STREAM, 0)` |
| 后台 fork | `fork\(\)\|daemon\(` | `pid = fork()` |

### 4.3 Go

| 模式 | Pattern | 示例 |
|------|---------|------|
| 裸 socket 监听 | `net\.Listen\(` | `net.Listen("tcp", ":8080")` |
| 嵌入式 DNS | `net\.LookupHost\|miekg/dns\|github.com/miekg/dns` | `dns.Server{Addr: ":53"}` |
| 后台 goroutine | `go\s+func\|goroutine` | `go func() {...}()` |

### 4.4 Java

| 模式 | Pattern | 示例 |
|------|---------|------|
| 裸 socket | `new\s+ServerSocket\(\|new\s+Socket\(` | `new ServerSocket(8080)` |
| NIO channel | `ServerSocketChannel\|Selector\.open` | `ServerSocketChannel.open()` |
| 后台线程 | `new\s+Thread\(\|ExecutorService` | `ExecutorService executor = ...` |

### 4.5 DNS / 网络服务识别

| 服务 | Pattern | 说明 |
|------|---------|------|
| DNS 服务 | `miekg/dns\|core/dns\|dnsmasq\|named\.conf` | DNS 服务器/解析器 |
| 嵌入式 socket | `net\.Listen\|socket\.socket\|ServerSocket` | 自定义 TCP/UDP 服务 |
| RPC 服务 | `grpc\.\|thrift\|net/rpc` | RPC 框架 |
| 消息队列 | `kafka\|rabbitmq\|nats\.\|pubsub` | 消息中间件 |

## 5. 判定逻辑

| 信号命中情况 | verdict | severity | status |
|-------------|---------|---------|--------|
| 命中 B/S 框架（Django/Flask/Spring/Express/Gin/Laravel/Rails 等） | `B/S 架构（Web 应用）` | info | PASS |
| 命中 C/S GUI（Qt/GTK/Swing/JavaFX/Electron/Tkinter 等） | `C/S 架构（桌面应用）` | info | PASS |
| 命中裸 socket / Telnet / daemon 模式 | `嵌入式或单机服务` | info | PASS |
| 同时命中 B/S 和 C/S | `混合架构（B/S + C/S）` | info | PASS |
| 无任何信号 | `unknown` | info | WARN |

## 6. 排除规则

下列情况下不进行架构推断：
- 文件类型为非文本（通过 `file` 命令识别）
- 文件大小 > 5MB（误匹配成本过高）
- 第三方库代码（在 allowlist 中标识）
- 生成代码（如 `*_pb.go`、`*.generated.*`）

## 7. 与其他维度联动

| 联动维度 | 用途 |
|---------|------|
| network-scanner | B/S 架构时启用 HTTP/HTTPS 协议深度检查 |
| secret-scanner | C/S 架构时优先检查本地凭证存储路径 |
| permission-scanner | 嵌入式服务时检查 setuid / privileged 标记 |
| crypto-scanner | B/S 架构时检查 HTTPS 强制与证书配置 |