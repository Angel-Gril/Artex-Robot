# 构建与打包

这个项目把 ARTEX 应用和 Norma SDK 保持成两个 Go module：

```text
根目录：module github.com/Autumn-27/artex
根目录 go.mod：require github.com/Autumn-27/norma v0.4.4
根目录 go.mod：replace github.com/Autumn-27/norma => ./norma
norma/go.mod：module github.com/Autumn-27/norma
```

这样既能离线构建 ARTEX，又不会把 Norma 改名成 ARTEX 的内部包。`norma/VERSION`、`norma/SOURCE.json` 和 `norma/LICENSE` 随源码一起保存，SDK 可以独立审计、测试和打包。

## 开发机依赖

- Go 1.26.3 或更高版本；
- Node.js 22 与 npm；
- Git；
- `rsync`（`build.sh` 同步前端静态文件）；
- `zip`；
- `sha256sum` 或 `shasum`；
- PostgreSQL 16（运行服务和数据库集成测试）；
- Docker + Buildx（可选，用于容器构建）；
- `sed`、`bash`、Python 3（脚本审查测试和部分技能）。

Windows 建议使用 WSL2 或 Git Bash；如果不需要本地跨平台压缩包，可以直接使用 Docker 构建。

## Norma 自动同步

每次执行 `build.sh`，默认会查询 Go Module Proxy 的稳定版本列表。如果发现版本高于本地 `norma/VERSION`，脚本会下载对应源码、校验 zip 路径、更新 `norma/`、根 `go.mod`、`norma/VERSION` 和 `norma/SOURCE.json`。

```bash
# 自动同步最新稳定版后再构建
./build.sh

# 只检查，不修改工作树；发现更新时返回非零
python3 scripts/sync-norma.py --check

# 固定某个版本
NORMA_VERSION=v0.4.4 ./build.sh

# 完全离线/可复现构建：使用提交中已锁定的版本
NORMA_AUTO_SYNC=0 ./build.sh
```

GitHub Release 工作流默认使用 `NORMA_AUTO_SYNC=0`，所以发布标签不会被构建机器上的更新版本悄悄改变。要更新 SDK，应先在开发分支运行自动同步，审阅 `norma/SOURCE.json` 和测试结果，再提交新的应用/SDK 版本。

## 验证两个 module

```bash
go mod download
go mod verify
go list -m all
go test ./...

# 根目录测试不会自动进入嵌套 norma module
cd norma
go test ./...
cd ..
```

## 本地编译 ARTEX

```bash
cd web
npm ci
npm run build:static
cd ..

rm -rf server/webui/dist
mkdir -p server/webui/dist
cp -a web/out/. server/webui/dist/

CGO_ENABLED=0 go build -tags embedui -trimpath \
  -ldflags "-s -w -buildid=" \
  -o artex ./cmd/artex
```

运行时使用 `./start.sh` 或 Windows 的 `start.bat`。

## 生成 ARTEX 应用包和独立 Norma 包

```bash
# 当前系统/架构
./build.sh

# 五个平台 ARTEX 应用包 + SHA256SUMS
ARTEX_BUILD_VERSION=v0.3.23-norma.0.4.4 ./build.sh --release

# 只打包 Norma v0.4.4，不重新编译 ARTEX
ARTEX_PACKAGE_DIR=dist ./build.sh --sdk
```

`--release` 生成各平台 ARTEX zip；`--sdk` 生成 `norma-v0.4.4.zip`。两者是独立文件，发布时共同写入 `SHA256SUMS`。

应用 zip 会带上可选的 `scripts/seep-mcp-guard.py`、`config/seep-mcp.example.json`、
`skills/seep-reverse/` 和 `docs/SEEP-INTEGRATION.md`。Seep 本体及其 GPL-3.0 工具链不随
ARTEX 包分发，按集成文档固定到独立 checkout 后再通过 MCP 连接。

## Docker 构建

```bash
docker compose build
docker compose up -d
```

Dockerfile 会在构建阶段运行前端导出和 Go 静态编译；Go 编译使用根目录的本地 Norma `replace`，不会从远程拉取 Norma 源码。若需要指定代理或镜像源：

```bash
docker build \
  --build-arg GOPROXY=https://proxy.golang.org,direct \
  --build-arg NPM_REGISTRY=https://registry.npmjs.org \
  -t artex-robot:local .
```

## 版本发布建议

应用版本和 SDK 版本不要合并成一个依赖号：

```text
ARTEX 基线：v0.3.15
ARTEX 维护更新：RuoJi6 v0.3.23
Norma：v0.4.4
组合发布标签：v0.3.23-norma.0.4.4
```

发布前至少执行：

```bash
go mod verify
go test ./...
(cd norma && go test ./...)
ARTEX_BUILD_VERSION=v0.3.23-norma.0.4.4 ./build.sh --release
```
