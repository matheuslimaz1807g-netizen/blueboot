#!/bin/bash
# diagnose-ssl.sh - Diagnóstico detalhado dos problemas SSL
# Execute na VPS: chmod +x diagnose-ssl.sh && ./diagnose-ssl.sh

echo "🔍 Diagnóstico SSL Detalhado"
echo "============================"

# 1. Verificar certificado
echo ""
echo "1️⃣ CERTIFICADO GERADO:"
if [ -f "ssl/live/bluebotapp.com.br/fullchain.pem" ]; then
    echo "✅ Arquivo fullchain.pem existe"
    echo "📅 Expira em: $(openssl x509 -in ssl/live/bluebotapp.com.br/fullchain.pem -enddate -noout | cut -d= -f2)"
    echo ""
    echo "🔗 Subject Alternative Names:"
    openssl x509 -in ssl/live/bluebotapp.com.br/fullchain.pem -text -noout | grep -A 10 "Subject Alternative Name" || echo "❌ SAN não encontrado"
else
    echo "❌ Certificado não encontrado"
fi

# 2. Verificar nginx
echo ""
echo "2️⃣ CONFIGURAÇÃO NGINX:"
if docker compose ps nginx | grep -q "Up"; then
    echo "✅ Nginx está rodando"
    echo ""
    echo "📄 Configuração SSL no nginx:"
    docker compose exec -T nginx nginx -T 2>/dev/null | grep -A2 -B2 "ssl_certificate" || echo "❌ Configuração SSL não encontrada"
else
    echo "❌ Nginx não está rodando"
fi

# 3. Testar conectividade
echo ""
echo "3️⃣ TESTE DE CONECTIVIDADE HTTPS:"
DOMAINS=("bluebotapp.com.br" "console.bluebotapp.com.br" "api.bluebotapp.com.br" "app.bluebotapp.com.br")

for domain in "${DOMAINS[@]}"; do
    echo ""
    echo "🌐 Testando $domain:"
    if curl -s --connect-timeout 10 "https://$domain/" > /dev/null 2>&1; then
        echo "  ✅ HTTPS: OK"
    else
        echo "  ❌ HTTPS: FALHA"
        # Tentar HTTP
        if curl -s --connect-timeout 10 "http://$domain/" > /dev/null 2>&1; then
            echo "  ⚠️  HTTP: OK (redirecionamento HTTPS pode estar falhando)"
        else
            echo "  ❌ HTTP: FALHA (problema de DNS ou conectividade)"
        fi
    fi
done

# 4. Verificar DNS
echo ""
echo "4️⃣ VERIFICAÇÃO DNS:"
for domain in "${DOMAINS[@]}"; do
    ip=$(dig +short "$domain" 2>/dev/null | head -1)
    if [ -n "$ip" ]; then
        echo "✅ $domain → $ip"
    else
        echo "❌ $domain → DNS FALHA"
    fi
done

# 5. Logs recentes
echo ""
echo "5️⃣ LOGS RECENTES DO NGINX:"
docker compose logs --tail=10 nginx 2>/dev/null || echo "❌ Não foi possível obter logs"

echo ""
echo "🎯 PRÓXIMOS PASSOS:"
echo "Baseado nos resultados acima, execute as correções necessárias."