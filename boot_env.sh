. ../setenv

# 1. 重新构建
#docker image rm dividend_backtesting
docker build \
  --build-arg DEV_UID=$(id -u) \
  --build-arg DEV_GID=$(id -g) \
  -t dividend_backtesting .

# 2. 停止并删除旧容器
docker stop dividend_backtesting || true
docker rm dividend_backtesting || true

cp -rf claude_config_backup
# 3. 启动（注意挂载路径）
docker run -dit \
  --name dividend_backtesting \
  --user dev \
  -e DEEPSEEK_API_KEY \
  -e MINIMAX_API_KEY \
  -v "$(pwd):/workspace" \
  dividend_backtesting
docker cp ./claude_config_backup/. dividend_backtesting:/home/dev/
docker exec dividend_backtesting ls -la /home/dev/ /workspace
docker exec dividend_backtesting printenv DEEPSEEK_API_KEY
docker exec dividend_backtesting printenv MINIMAX_API_KEY
docker exec dividend_backtesting sh -c 'sed -i "s|REPLACE_ANTHROPIC_AUTH_TOKEN|$DEEPSEEK_API_KEY|g" /home/dev/.claude/settings.json'
docker exec dividend_backtesting cat /home/dev/.claude/settings.json
docker exec dividend_backtesting pip install /workspace