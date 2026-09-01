#!/usr/bin/env bash
# 构建 OntoMind opencode 镜像
#
# 用法：
#   ./build.sh                    # 构建 latest
#   ./build.sh 1.18.4             # 构建指定 opencode 版本
#   PLATFORM=linux/amd64 ./build.sh   # 交叉构建（默认跟随本机架构）

set -euo pipefail

cd "$(dirname "$0")"

VERSION="${1:-latest}"
IMAGE="ontomind/opencode:${VERSION}"
PLATFORM="${PLATFORM:-}"

echo "==> 构建 ${IMAGE}"
[[ -n "${PLATFORM}" ]] && echo "==> 目标平台: ${PLATFORM}"

BUILD_ARGS=(--build-arg "OPENCODE_VERSION=${VERSION}" -t "${IMAGE}")
[[ -n "${PLATFORM}" ]] && BUILD_ARGS+=(--platform "${PLATFORM}")

docker build "${BUILD_ARGS[@]}" .

# latest 额外打个不带 tag 的别名，方便 DockerService 默认配置引用
if [[ "${VERSION}" == "latest" ]]; then
  docker tag "${IMAGE}" ontomind/opencode:latest
fi

echo ""
echo "==> 构建完成"
docker images | grep -E "^REPOSITORY|ontomind/opencode" || true

echo ""
echo "==> 快速验证（不需要 API Key）"
echo "docker run --rm ${IMAGE} --version"
echo ""
echo "==> 启动单个实例"
echo "docker run -d --name oc-test -p 4201:4096 \\"
echo "  -e ARK_API_KEY=\$ARK_API_KEY \\"
echo "  -e OPENCODE_CORS=http://localhost:5173 \\"
echo "  -v \$HOME/.config/opencode/agent:/root/.config/opencode/agent:ro \\"
echo "  ${IMAGE}"
echo ""
echo "==> 探活"
echo "curl -s http://127.0.0.1:4201/global/health"
