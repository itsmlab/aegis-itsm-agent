# AEGIS PATTERNS
## Knowledge Base for Autonomous Incident Triage Agent

**Version:** 2.0
**Last Updated:** 2026-06-16
**Total Patterns:** 20

---

## Pattern AEGIS-001
**Name:** Cascade Dependency Saturation
**Source:** AWS Kinesis Event - November 25, 2020
**URL:** https://aws.amazon.com/message/11201/

### Symptoms (automatically detectable)

| Symptom | Where to see | Typical format |
|---------|--------------|----------------|
| API returns 500/503 | HTTP Responses | `HTTP/1.1 503 Service Unavailable` |
| Latency increases to timeout | APM Metrics | `p99 latency: 500ms → 30s → timeout` |
| Throttling triggered | CloudWatch/Datadog | `WriteProvisionedThroughputExceeded > 10%` |
| Specific exception | Application logs | `AmazonKinesisException`, `RetryableKinesisException` |
| Slow dependency | Distributed tracing | `span duration > 5s in metadata service` |

### Diagnosis (root cause)

**Phenomenon:** Domino effect from non-resilient dependency.

Primary service (A) depends on secondary service (B) to operate. B becomes slow (not necessarily down). A has no timeouts or circuit breakers configured. Each request to A waits for B's response. A's connection pool exhausts. New requests cannot enter. A starts rejecting traffic or returning errors.

**In AWS Kinesis case:**
- Service A: Kinesis API (front-end)
- Service B: Internal metadata and permissions system
- Cause of B slowdown: Spike of malformed requests

### Remediation Script

```bash
#!/bin/bash
# AEGIS-001: Remediation for cascade dependency saturation

set -e

echo "[AEGIS] Detecting saturated dependency..."

# 1. IDENTIFY slow dependency (example with microservices)
SLOW=$(kubectl get pods --all-namespaces -o json | jq -r '.items[] | select(.metadata.annotations."prometheus.io/port" != null) | .metadata.namespace + "/" + .metadata.name' | head -1)

echo "[AEGIS] Possible slow dependency: $SLOW"

# 2. ACTIVATE circuit breaker (if endpoint exists)
if curl -s -f "http://api-gateway/actuator/circuitbreakers" > /dev/null 2>&1; then
    echo "[AEGIS] Activating circuit breaker..."
    curl -X POST "http://api-gateway/actuator/circuitbreakers/cb-dependencies/transition/FORCED_OPEN"
fi

# 3. SCALE UP the dependency
echo "[AEGIS] Scaling up dependency..."
kubectl scale deployment/auth-service --replicas=10 --timeout=60s

# 4. CLEAN dead connections
echo "[AEGIS] Cleaning exhausted connections..."
kubectl delete pods -l app=api-gateway --field-selector=status.phase=Failed

# 5. RESTART in reverse order (dependents first)
echo "[AEGIS] Restarting services (reverse dependency order)..."
for service in api-gateway kinesis-frontend; do
    kubectl rollout restart deployment/$service
    sleep 30
    kubectl rollout status deployment/$service
done

# 6. VERIFY recovery
echo "[AEGIS] Verifying final status..."
if curl -s -f -w "%{http_code}\n" "http://api-gateway/health" -o /dev/null | grep -q "200"; then
    echo "[AEGIS] ✅ Service successfully recovered"
else
    echo "[AEGIS] ⚠️ Manual verification needed - possible collateral damage"
fi
```

---

## Pattern AEGIS-002
**Name:** Human Error During Deployment
**Source:** AWS S3 US-EAST-1 - February 28, 2017

### Symptoms
- Service stops responding completely (no error, just timeout)
- Monitoring shows 0% availability immediately after deployment
- Manual rollback resolves the problem instantly

### Diagnosis
A mistyped command or invalid configuration was deployed to production. The pre-validation system did not detect the error. The service could not start with the corrupted configuration.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-002: Remediation for human deployment error

# 1. Immediate rollback to last known good state
kubectl rollout undo deployment/my-service

# 2. Validate new configuration before retrying
if yamllint new-config.yaml; then
    echo "Config valid, retrying deployment"
    kubectl apply -f new-config.yaml
else
    echo "YAML syntax error, deployment blocked"
fi

# 3. Notify the team
echo "Deployment failed due to syntax error. Rollback executed." | \
    tee /var/log/aegis/deployment-error.log
```

---

## Pattern AEGIS-003
**Name:** Rate Limiting / Throttling from Unexpected Spike
**Source:** AWS DynamoDB - September 2021

### Symptoms
- API returns error 429 (Too Many Requests)
- Normal latency, but many requests fail
- Users report intermittent errors
- No change in application code
- Throttling metric spikes

### Diagnosis
A client (user, script, or integration) is making requests too quickly. Could be a bug (infinite loop), attack (DDoS), or misconfigured batch job. Rate limit exists but there's no client authentication to isolate the culprit.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-003: Remediation for rate limiting / throttling

# 1. Identify client making the most requests
aws dynamodb scan --table-name YourTable --attributes-to-get "client_id" \
  | jq '.Items | group_by(.client_id) | map({client: .[0].client_id, count: length}) | sort_by(.count) | reverse | .[0]'

# 2. Apply specific throttle to that client
aws dynamodb update-table --table-name YourTable \
  --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=50

# 3. Block client if malicious
iptables -A INPUT -s CLIENT_IP -j DROP

# 4. Alert the team
echo "Possible DDoS attack or infinite script from $CLIENT_IP" | \
    mail -s "Rate limit exceeded" security@yourcompany.com
```

---

## Pattern AEGIS-004
**Name:** Cold Starts and Concurrency
**Source:** AWS Lambda - June 2022

### Symptoms
- First request after inactivity is very slow (5-10 seconds)
- Subsequent requests are fast (<100ms)
- Traffic spikes cause intermittent timeouts
- Function scales but some executions fail
- Logs show long "Init duration"

### Diagnosis
The serverless function was idle and had to initialize from zero (cold start). Large dependencies or heavy code take time to load. During traffic spikes, new instances also go through cold starts, causing latency and potential timeouts.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-004: Remediation for cold starts and concurrency

# 1. Increase memory (also increases CPU)
aws lambda update-function-configuration \
  --function-name my-function \
  --memory-size 2048

# 2. Configure provisioned concurrency (keep instances warm)
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier PROD \
  --provisioned-concurrent-executions 5

# 3. Keep warm with periodic ping
# (CloudWatch Event every 5 minutes)
aws events put-rule \
  --name keep-warm-my-function \
  --schedule-expression "rate(5 minutes)"

# 4. Optimize dependencies (team recommendation)
# Move heavy dependencies outside handler
# Use Lambda layers for shared dependencies
```

---

## Pattern AEGIS-005
**Name:** Database Failover
**Source:** AWS RDS - March 2023

### Symptoms
- Application shows database connection errors
- Previously fast queries now take seconds
- Logs show "connection refused" or "timeout"
- Replica lag metric increases suddenly
- Application still works but with inconsistent data or slowness

### Diagnosis
The primary database failed (maintenance, error, or saturation). Automatic failover promoted a replica to primary. During failover (30-120 seconds), connections are lost. After failover, the new primary may have cold caches or different performance characteristics.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-005: Remediation for database failover

# 1. Verify failover status
aws rds describe-db-instances \
  --db-instance-identifier my-db \
  --query 'DBInstances[0].StatusInfos'

# 2. Reconnect application (restart connection pools)
kubectl rollout restart deployment/api
kubectl rollout restart deployment/workers

# 3. Verify replica lag after failover
aws rds describe-db-instances \
  --db-instance-identifier my-db-replica \
  --query 'DBInstances[0].ReadReplicaDBInstanceIdentifiers'

# 4. Warm up cache (PostgreSQL example)
psql -h new-primary -d my-db -c "SELECT pg_prewarm('large_table');"

# 5. Alert DBA team
echo "Failover detected on database. Verify data consistency." | \
    mail -s "Database Failover Alert" dba@yourcompany.com
```

---

## Pattern AEGIS-006
**Source:** Cloudflare - DNS outage, July 2022

### Symptoms
- Metric `dns_query_timeout` spikes >30% of queries
- Internal resolver logs: `resolution failed: SERVFAIL` or `connection refused`
- Monitoring alert: `DNS resolution latency p99 > 5s` (baseline: 50ms)
- Origin health checks fail intermittently
- HTTP 5xx traffic increases proportionally to DNS failures

### Diagnosis
Routing loop in the Anycast global load balancing layer. DNS packets traveled between two data centers in an infinite loop due to mis-propagated BGP prefix configuration. This caused TTL exhaustion in the internal network, saturating edge routers. The control plane remained operational but the data plane (DNS queries) could not resolve.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-006: Mitigation for DNS/Anycast routing loop

# 1. Identify problematic BGP peers
vtysh -c "show ip bgp neighbors" | grep -E "(State|Prefixes)" | grep -B1 "Idle"

# 2. Temporarily withdraw suspicious routes
vtysh -c "configure terminal" \
      -c "route-map BLOCK_DNS_LOOP permit 10" \
      -c "set community 65534:666" \
      -c "router bgp 64512" \
      -c "neighbor CLOUDFLARE_PEER route-map BLOCK_DNS_LOOP out"

# 3. Flush DNS cache on all internal resolvers
for resolver in $(dig +short resolvers.internal.prod); do
    ssh "$resolver" "systemd-resolve --flush-caches && rndc flush"
done

# 4. Verify manual resolution
dig @8.8.8.8 google.com +tries=1 +timeout=2 || \
curl -H "Host: health-check" http://169.254.169.254/health

# 5. If persists, activate fallback to tertiary resolvers
sed -i 's/nameserver 1.1.1.1/nameserver 8.8.8.8/g' /etc/resolv.conf
systemctl restart systemd-resolved
```

---

## Pattern AEGIS-007
**Source:** Google SRE Book / Outage - Bigtable cluster partition, 2016

### Symptoms
- Metric `replication_lag` between shards > 60 seconds
- Chubby lock logs: `lock acquisition timeout` or `paxos_lease_expired`
- Consistency alerts: `data_version_mismatch` between replicas
- p99 read latency jumps from 10ms to >2s
- API returns `500 Internal Error` with message `unavailable_for_partition`

### Diagnosis
Network partition between two availability zones of the Bigtable cluster. The lock service (Chubby) lost quorum (3 of 5 nodes unreachable). Without locks, writes could not be confirmed cross-zone. The system entered "fail-strict" mode to avoid split-brain, stopping write operations for 47 minutes.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-007: Resolution for Bigtable/Chubby partition

# 1. Identify zone with available quorum
QUORUM_ZONE=$(gcloud compute regions describe us-central1 \
    --format="value(name)" | head -1)

# 2. Force leader election in zone with majority
gcloud bigtable clusters update "$QUORUM_ZONE" \
    --force-election --leader-priority=high

# 3. Isolate non-responsive zone
gcloud compute firewall-rules create deny-failed-zone \
    --direction=INGRESS --priority=1000 \
    --source-ranges=10.0.1.0/24 --action=DENY \
    --rules=all

# 4. Rebuild Chubby leases
for table in $(gcloud bigtable tables list); do
    cbt -project "$PROJECT" -instance "$INSTANCE" \
        recreatelease "$table" --force
done

# 5. Restore replication
gcloud bigtable clusters update us-central1 \
    --num-nodes=5 --autoscaling-max-nodes=10
```

---

## Pattern AEGIS-008
**Source:** GitHub - MySQL database outage, October 2021

### Symptoms
- MySQL logs: `Waiting for table metadata lock` (thousands of entries)
- Metric `threads_running` > 1000 (baseline: 50-100)
- Monitoring alerts: `replication_delay` > 300 seconds
- GitHub API returns `500` with `ActiveRecord::LockTimeout`
- `SHOW PROCESSLIST` queries show `Updating` state > 300 seconds

### Diagnosis
A schema migration (ALTER TABLE) on a 3TB table blocked metadata. The migration ran without `pt-online-schema-change`. A second script tried to read the same table and got stuck waiting. Replication threads cascaded into blocking, saturating the connection pool and stopping new connections.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-008: Mitigation for MySQL metadata lock

# 1. Identify blocked connections
mysql -e "SELECT * FROM information_schema.INNODB_TRX\G" | \
    grep -E "(trx_id|trx_state|trx_started)"

# 2. Kill blocked queries (kill by trx_mysql_thread_id)
for id in $(mysql -e "SELECT trx_mysql_thread_id FROM information_schema.INNODB_TRX WHERE trx_state='LOCK WAIT'"); do
    mysql -e "KILL $id"
done

# 3. Force metadata lock release
mysql -e "FLUSH TABLES WITH READ LOCK; UNLOCK TABLES;"

# 4. Use pt-online-schema-change for future migrations
pt-online-schema-change --alter "ADD COLUMN new_col INT" \
    D=production,t=users --execute --chunk-size=10000

# 5. Restore replica
mysql -e "STOP SLAVE; START SLAVE; SHOW SLAVE STATUS\G" | \
    grep -E "(Seconds_Behind_Master|Slave_IO_Running)"
```

---

## Pattern AEGIS-009
**Source:** Netflix Tech Blog / Chaos Engineering - Cassandra cluster saturation, 2018

### Symptoms
- Metric `cassandra_read_timeout` > 20% of all queries
- Logs: `ReadTimeoutException`, `Request timed out while waiting for replica`
- p99 latency of API consuming Cassandra jumps from 50ms to >5s
- Cassandra nodes in `UN` (Up Normal) state but hinted_handoff pending >1M
- Alerts for `compaction_pending_tasks` > 100 per node

### Diagnosis
Chaos Engineering experiment caused massive failover. Three datacenters lost connectivity simultaneously due to latency injection. Each node tried to compensate writes using hinted_handoff, generating 2TB of pending compactions. Nodes didn't die but became so slow they consistently timed out.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-009: Recovery for saturated Cassandra post-Chaos

# 1. Disable hinted_handoff to avoid cascade
nodetool sethintedhandoffthrottlekb 0
nodetool disablehintedhandoff

# 2. Force selective compactions by table
for table in $(cqlsh -e "DESCRIBE TABLES" | grep -v system); do
    nodetool compact keyspace "$table"
done

# 3. Clean pending hints
nodetool trashhints
find /var/lib/cassandra/hints/ -type f -delete

# 4. Temporarily reduce consistency (minimum read-your-writes)
cqlsh -e "ALTER KEYSPACE production WITH REPLICATION = {'class': 'NetworkTopologyStrategy', 'DC1': 2, 'DC2': 2} AND DURABLE_WRITES = false"

# 5. Gradually re-enable hinted_handoff
nodetool sethintedhandoffthrottlekb 1024
nodetool enablehintedhandoff

# 6. Verify status
nodetool status
nodetool compactionstats
```

---

## Pattern AEGIS-010
**Source:** Cloudflare - BGP leak & Internet outage, June 2024

### Symptoms
- Global traffic drops >50% in less than 3 minutes
- Metric `bgp_prefix_count` spikes from 900k to 4M+ routes
- Router logs: `BGP UPDATE with AS_PATH length 255`
- NOC alerts: `Blackhole detection triggered /0 route received`
- Users report site unreachable from multiple ISPs

### Diagnosis
A small ASN accidentally published more specific routes (/24 and /23) of Cloudflare's /16 prefixes. A second ASN propagated these routes without filtering. The result was a BGP route leak that diverted global traffic through routers with insufficient capacity, creating an accidental DDoS. The BGP control plane converged but the data plane collapsed.

### Remediation Script
```bash
#!/bin/bash
# AEGIS-010: Mitigation for BGP route leak

# 1. Identify non-owned received prefixes
vtysh -c "show ip bgp neighbors AS65000 advertised-routes" | \
    grep -E "via|prefix" | grep -v "AS13335"

# 2. Apply strict as-path filters (direct AS only)
vtysh -c "configure terminal" \
      -c "ip as-path access-list DENY_LEAK deny _65000_" \
      -c "route-map FILTER_LEAK permit 10" \
      -c "match as-path DENY_LEAK"

# 3. Withdraw poisoned routes
vtysh -c "clear ip bgp * soft out"

# 4. Flush BGP cache on all routers
for router in $(ansible-inventory --list | jq -r '.routers | keys[]'); do
    ansible "$router" -m command -a "vtysh -c 'clear bgp *'"
done

# 5. Verify final BGP table
vtysh -c "show ip bgp summary" | grep -E "(prefixes|neighbor)"

# 6. Notify NOC team
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"BGP leak mitigated - invalid routes withdrawn"}' \
    "$SLACK_WEBHOOK"
```

---

## Change Log

| Date | Pattern | Change |
|------|---------|--------|
| 2026-06-08 | AEGIS-001 to 010 | Complete translation to English |
| 2026-06-06 | AEGIS-001 | Initial creation from AWS Kinesis 2020 |

---

## Next Patterns (Planned)

- [ ] AEGIS-011: Kubernetes etcd quorum loss
- [ ] AEGIS-012: Redis memory fragmentation
- [ ] AEGIS-013: NGINX upstream flood
- [ ] AEGIS-014: Kafka leader election storm
- [ ] AEGIS-015: Elasticsearch cluster split-brain

---

# AEGIS Azure Patterns — Knowledge Base Extension
## 10 Additional Patterns from Azure Status History (2022–2026)

---

## Pattern AEGIS-011
**Source:** Azure OpenAI Service — Latency and Intermittent Failures (May 2026, Tracking ID: LYXT-C1Z)
**Priority:** HIGH

### Symptoms
- Increased latency on inference requests to Azure OpenAI or LLM endpoints
- Intermittent HTTP 5XX errors (500, 503) on AI/ML API calls
- Retry storms visible in logs — single requests generating 10-50+ retries
- Impact more pronounced in specific regions (Europe, Australia)
- Underlying customer demand unchanged but internal traffic exploding

### Diagnosis
**Retry amplification cascade.** An upstream change altered how capacity-related failures were surfaced, causing multiple layers to interpret transient failures as retriable. Without sufficient backoff or jitter, a single failed request triggered up to 48 retry attempts, creating a retry storm that overwhelmed the shared inference routing layer. The issue was masked initially because traffic naturally declined in the first affected region, obscuring the real cause until a higher-traffic region was impacted.

### Root Cause Pattern
Internal dependency API change → failure response format changed → upstream layers retry aggressively → retry amplification → shared routing layer resource exhaustion → OOM crashes → broad degradation

### Remediation Script
```bash
# AEGIS-011: Retry Amplification Cascade — Azure OpenAI / LLM endpoints

# 1. Identify retry storm in application logs
grep -E "retry|5[0-9]{2}|timeout" /var/log/app/*.log | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -20

# 2. Immediately enable exponential backoff with jitter in retry logic
# (Emergency config — apply to load balancer or API gateway)
# Azure API Management policy example:
cat << 'EOF'
<retry condition="@(context.Response.StatusCode >= 500)" count="3" interval="2" delta="2" max-interval="10">
    <wait duration="@(new Random().Next(1, 3))" />
    <forward-request />
</retry>
EOF

# 3. Check current retry counts per service
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{name} \
  --metric "TotalCalls,SuccessfulCalls,TotalErrors" \
  --interval PT1M

# 4. Apply circuit breaker — temporarily reject retries to reduce load
# In Azure API Management: set retry count to 0 temporarily
az apim api policy update \
  --resource-group {rg} \
  --service-name {apim} \
  --api-id {api-id} \
  --value '<policies><inbound><base /></inbound><backend><retry condition="false" count="0"><forward-request /></retry></backend></policies>'

# 5. Scale out affected routing layer
az vmss scale \
  --resource-group {rg} \
  --name {vmss-name} \
  --new-capacity 10

# 6. Monitor recovery
az monitor metrics list \
  --resource {resource-id} \
  --metric "Latency,Errors" \
  --interval PT1M \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)
```

### Generalization
Applies to: Any service with retry logic without proper backoff/jitter — REST APIs, microservices, message queues, Azure Service Bus, Azure Event Hubs, Azure Functions with retry policies.

---

## Pattern AEGIS-012
**Source:** Azure Virtual Machines + Managed Identities — Control Plane Failures (February 2026, Tracking ID: FNJ8-VQZ)
**Priority:** HIGH

### Symptoms
- VM provisioning and scaling operations failing across multiple regions
- Errors during VM lifecycle operations (start, stop, resize, deploy)
- Managed Identity token acquisition failures — HTTP 429 or 503
- Azure Resource Manager (ARM) API calls timing out
- Multiple Azure services degraded simultaneously (cascading from VM layer)

### Diagnosis
**Platform-level control plane failure.** A platform issue caused degraded performance in the Azure compute control plane, affecting VM management operations and cascading to services that depend on Managed Identities for authentication. Services relying on ARM for resource management lost the ability to perform operations, causing broad multi-service impact.

### Root Cause Pattern
Azure platform control plane issue → VM operations fail → Managed Identity token endpoint degraded → Services using MSI for auth lose access → Cascade to dependent services

### Remediation Script
```bash
# AEGIS-012: Azure Control Plane / Managed Identity Failure

# 1. Verify if issue is platform-wide (check Azure Status)
curl -s https://azure.status.microsoft/api/v2/status.json | \
  python3 -c "import sys,json; s=json.load(sys.stdin); print(s['status']['description'])"

# 2. Test Managed Identity token acquisition
curl -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/"

# 3. Implement fallback authentication (Service Principal)
az login --service-principal \
  --username $SP_CLIENT_ID \
  --password $SP_CLIENT_SECRET \
  --tenant $TENANT_ID

# 4. Check ARM API health
az group list --query "[0].name" 2>&1 | head -5

# 5. For VMs stuck in transitioning state — force deallocate
az vm deallocate \
  --resource-group {rg} \
  --name {vm-name} \
  --no-wait

# 6. For AKS nodes failing — cordon affected nodes
kubectl get nodes
kubectl cordon {node-name}
kubectl drain {node-name} --ignore-daemonsets --delete-emptydir-data

# 7. Monitor VM operations
az monitor activity-log list \
  --resource-group {rg} \
  --start-time $(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --query "[?contains(status.value, 'Failed')]" \
  --output table
```

### Generalization
Applies to: Any Azure workload using Managed Identities, ARM-dependent operations, AKS node pools, Azure Functions with MSI, App Service with system-assigned identities.

---

## Pattern AEGIS-013
**Source:** Azure Front Door + CDN — DDoS Mitigation Misconfiguration (July 2024, Tracking ID: KTY1-HW8)
**Priority:** HIGH

### Symptoms
- Intermittent connection errors, timeouts, or latency spikes on public endpoints
- Azure Front Door returning 503 or connection reset errors
- CDN-served content intermittently unavailable
- Azure Portal itself intermittently inaccessible
- Impact on Microsoft 365 and downstream services
- Issue started after a DDoS mitigation action was applied

### Diagnosis
**DDoS mitigation misconfiguration causing self-inflicted congestion.** After applying a routine DDoS mitigation, a network misconfiguration caused congestion and packet loss on Azure Front Door frontends. The mitigation action intended to protect the platform instead created network-level packet loss affecting legitimate traffic.

### Root Cause Pattern
DDoS attack detected → mitigation applied → network misconfiguration introduced → packet loss on AFD frontends → connection timeouts for legitimate traffic → cascading impact on portal and M365

### Remediation Script
```bash
# AEGIS-013: Azure Front Door / CDN Connectivity Degradation

# 1. Verify AFD health
az network front-door check-custom-https \
  --resource-group {rg} \
  --name {frontdoor-name} \
  --frontend-endpoint {endpoint}

# 2. Test connectivity to AFD origin directly (bypass AFD)
curl -v --connect-timeout 10 https://{origin-hostname}/health

# 3. Check if issue is AFD-specific or origin
# Compare direct origin vs AFD endpoint response times
for i in {1..5}; do
  echo "Direct origin:"
  curl -o /dev/null -s -w "%{time_total}\n" https://{origin}
  echo "Via AFD:"
  curl -o /dev/null -s -w "%{time_total}\n" https://{afd-endpoint}
done

# 4. Implement client-side retry with backoff
# Add to application configuration:
cat << 'EOF'
Retry-After: 5
Connection retry logic: exponential backoff (1s, 2s, 4s, 8s max)
EOF

# 5. If AFD is the issue — temporarily route traffic to origin directly
az network front-door routing-rule update \
  --resource-group {rg} \
  --front-door-name {name} \
  --name {routing-rule} \
  --forwarding-protocol HttpsOnly \
  --backend-pool {pool}

# 6. Monitor AFD metrics
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/frontdoors/{name} \
  --metric "RequestCount,BackendHealthPercentage,TotalLatency" \
  --interval PT1M
```

### Generalization
Applies to: Any workload behind Azure Front Door, Azure CDN, Application Gateway, Traffic Manager. Also relevant when DDoS Protection Standard is enabled.

---

## Pattern AEGIS-014
**Source:** Azure Front Door + CDN — DNS Resolution Failure (October 2025, Tracking ID: YKYN-BWZ)
**Priority:** HIGH

### Symptoms
- Connection timeout errors on AFD/CDN endpoints
- DNS resolution failures for Azure Front Door domains (*.azurefd.net)
- Gradual recovery with increased latency before full stabilization
- Impact lasting 8+ hours with partial recovery periods
- Services behind AFD returning NXDOMAIN or DNS timeout

### Diagnosis
**Azure Front Door DNS infrastructure failure.** DNS resolution for AFD endpoints failed, preventing clients from resolving the IP addresses needed to reach AFD frontends. Unlike a typical DDoS scenario, this was an infrastructure-level DNS failure affecting the AFD routing layer, causing both timeout errors and DNS resolution failures simultaneously.

### Root Cause Pattern
AFD DNS infrastructure degradation → DNS resolution failures for *.azurefd.net → Client connections cannot be established → Services behind AFD become unreachable → Gradual recovery as DNS propagates

### Remediation Script
```bash
# AEGIS-014: Azure Front Door DNS Resolution Failure

# 1. Diagnose DNS resolution
nslookup {your-frontdoor}.azurefd.net 8.8.8.8
dig {your-frontdoor}.azurefd.net @1.1.1.1
dig {your-frontdoor}.azurefd.net @168.63.129.16  # Azure DNS

# 2. Test with alternative DNS resolvers
for dns in 8.8.8.8 1.1.1.1 9.9.9.9; do
  echo "Testing DNS $dns:"
  dig @$dns {your-frontdoor}.azurefd.net +short
done

# 3. If DNS fails — use IP-based routing temporarily
# Get last known AFD IP
nslookup {your-frontdoor}.azurefd.net | grep -A1 "Name:" | grep "Address"

# 4. Add hosts file entry as emergency bypass (temporary)
echo "{afd-ip} {your-frontdoor}.azurefd.net" >> /etc/hosts

# 5. Update Traffic Manager to bypass AFD
az network traffic-manager profile update \
  --resource-group {rg} \
  --name {tm-profile} \
  --routing-method Priority

# 6. Enable direct origin routing in application config
# Update DNS CNAME to point directly to origin
az network dns record-set cname set-record \
  --resource-group {rg} \
  --zone-name {zone} \
  --record-set-name {record} \
  --cname {origin-hostname}

# 7. Monitor DNS propagation
watch -n 30 "dig {your-frontdoor}.azurefd.net +short"
```

### Generalization
Applies to: Any service using Azure Front Door, custom domains on AFD, applications relying on *.azurefd.net DNS resolution.

---

## Pattern AEGIS-015
**Source:** Azure West Europe — Multi-Service Regional Disruption (November 2025, Tracking ID: 2LGD-9VG)
**Priority:** HIGH

### Symptoms
- Multiple services degraded simultaneously in a single Azure region
- VM, PostgreSQL, MySQL, AKS, Storage, Service Bus all affected
- Databricks cluster launch and scaling failures
- Errors span compute, database, storage, and messaging layers
- Other regions unaffected — issue isolated to one region

### Diagnosis
**Regional infrastructure failure causing multi-service cascade.** A platform-level issue in a single Azure region caused degraded performance across all services sharing that region's underlying infrastructure. When Azure's regional compute fabric experiences issues, services that depend on it — databases, storage, containers, messaging — all degrade simultaneously.

### Root Cause Pattern
Regional infrastructure platform issue → Shared compute/network fabric degraded → All services in region affected → Multi-service cascade → Recovery requires platform-level remediation by Microsoft

### Remediation Script
```bash
# AEGIS-015: Azure Regional Multi-Service Disruption

# 1. Confirm regional scope — check multiple services in same region
az vm list --query "[?location=='{region}'].{name:name,status:provisioningState}" -o table
az postgres flexible-server list --query "[?location=='{region}'].{name:name,state:state}" -o table

# 2. Check Azure Service Health for the region
az rest --method GET \
  --url "https://management.azure.com/subscriptions/{sub}/providers/Microsoft.ResourceHealth/availabilityStatuses?api-version=2022-10-01&$filter=Location eq '{region}'" \
  --query "value[].{resource:id,status:properties.availabilityState}" -o table

# 3. Initiate regional failover if geo-redundancy configured
# For AKS — switch to secondary cluster
kubectl config use-context {secondary-cluster}
kubectl get nodes

# 4. For Azure Database — promote geo-replica
az postgres flexible-server replica promote \
  --resource-group {rg} \
  --name {replica-name}

# 5. Update Traffic Manager to redirect to secondary region
az network traffic-manager endpoint update \
  --resource-group {rg} \
  --profile-name {tm-profile} \
  --name {primary-endpoint} \
  --type azureEndpoints \
  --endpoint-status Disabled

# 6. For Storage — switch to secondary endpoint (RA-GRS)
# Update connection string to use -secondary endpoint:
# https://{account}-secondary.blob.core.windows.net

# 7. Notify stakeholders and set up status page
az communication email send \
  --connection-string {conn} \
  --sender {sender} \
  --to {ops-team} \
  --subject "Regional failover initiated — {region}" \
  --text "Activating DR plan for Azure {region} disruption. ETA: 30 minutes."
```

### Generalization
Applies to: Any Azure workload without geo-redundancy. High priority for production workloads in single-region deployments. Trigger for business continuity / DR plan activation.

---

## Pattern AEGIS-016
**Source:** Azure Active Directory / Entra ID — Sign-In and Auth Failures (June 2022)
**Priority:** HIGH

### Symptoms
- Users unable to sign in to Azure portal or Microsoft 365
- Azure AD / Entra ID authentication returning 500 or timeout errors
- Service Principal authentication failing for automated workloads
- Azure Monitor, Log Analytics, Application Insights losing telemetry
- Azure Resource Manager API calls failing with auth errors

### Diagnosis
**Azure Active Directory / Entra ID disruption.** AAD/Entra ID is the authentication backbone for all Azure services. When it experiences issues, every service requiring OAuth2 tokens or SAML authentication becomes degraded. Automated workloads using Service Principals or Managed Identities are particularly vulnerable.

### Root Cause Pattern
Entra ID / AAD service disruption → Token issuance fails → All OAuth2/SAML dependent services lose auth → Azure portal, M365, automated workloads all affected → Recovery requires Microsoft platform remediation

### Remediation Script
```bash
# AEGIS-016: Azure AD / Entra ID Authentication Failure

# 1. Verify AAD connectivity
curl -s "https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration" | \
  python3 -c "import sys,json; print('AAD reachable:', 'issuer' in json.load(sys.stdin))"

# 2. Test token acquisition
curl -X POST "https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token" \
  -d "client_id={client-id}&client_secret={secret}&grant_type=client_credentials&scope=https://management.azure.com/.default"

# 3. Check AAD status
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/issues" \
  --query "value[?contains(service,'Azure Active Directory')]" -o table 2>/dev/null || \
  echo "Check https://admin.microsoft.com/adminportal/home#/servicehealth"

# 4. For workloads — implement cached token fallback
# Most Azure SDKs cache tokens — verify cache is used:
# Python (azure-identity): DefaultAzureCredential has built-in cache
# .NET: TokenCredential caches by default for 5 minutes before expiry

# 5. Extend token cache TTL temporarily (application-level)
# For applications using MSAL:
echo "Set token cache persistence — tokens remain valid 1 hour"
echo "Implement token refresh retry with 60-second intervals"

# 6. Monitor AAD sign-in logs when service recovers
az monitor log-analytics query \
  --workspace {workspace-id} \
  --analytics-query "SigninLogs | where TimeGenerated > ago(2h) | summarize count() by ResultType, bin(TimeGenerated, 5m)" \
  --timespan PT2H
```

### Generalization
Applies to: Every Azure workload using AAD/Entra ID authentication — which is virtually all of them. Priority: implement token caching and fallback auth for all production workloads.

---

## Pattern AEGIS-017
**Source:** Azure Firewall + Data Explorer — Multi-Region Disruption (June 2022)
**Priority:** HIGH

### Symptoms
- Azure Firewall dropping traffic or becoming unresponsive
- Network connectivity loss for workloads behind Azure Firewall
- Azure Data Explorer queries timing out or failing
- Azure Synapse Analytics, Azure Backup, Azure Stream Analytics degraded
- Multiple waves of WARN/UP status — intermittent partial recovery

### Diagnosis
**Azure Firewall infrastructure failure with cascading impact.** Azure Firewall, when it fails, creates a total network blackout for workloads routing traffic through it. The intermittent WARN/UP pattern indicates the firewall was partially processing traffic — enough to appear recovered but not enough to maintain stable connectivity. Services that depend on Firewall-protected networks (Data Explorer, Synapse) cascaded.

### Root Cause Pattern
Azure Firewall infrastructure issue → Traffic routing through firewall drops → Protected workloads lose network connectivity → Dependent services (Data Explorer, Synapse) cascade → Intermittent recovery masks true extent of failure

### Remediation Script
```bash
# AEGIS-017: Azure Firewall Failure / Network Connectivity Loss

# 1. Verify Azure Firewall health
az network firewall show \
  --resource-group {rg} \
  --name {firewall-name} \
  --query "{state:provisioningState, threatIntelMode:threatIntelMode}"

# 2. Check firewall policy
az network firewall policy show \
  --resource-group {rg} \
  --name {policy-name} \
  --query "provisioningState"

# 3. Test connectivity through firewall
nc -zv {destination-ip} {port} -w 5

# 4. Emergency bypass — route critical traffic around firewall
# Update UDR (User Defined Route) to bypass firewall temporarily
az network route-table route update \
  --resource-group {rg} \
  --route-table-name {udr-name} \
  --name {route-name} \
  --next-hop-type Internet  # EMERGENCY ONLY — removes firewall protection

# 5. Restart firewall (deallocate and reallocate)
az network firewall deallocate \
  --resource-group {rg} \
  --name {firewall-name}

# Wait 2 minutes
sleep 120

VNET_ID=$(az network vnet show -g {rg} -n {vnet} --query id -o tsv)
PUBIP_ID=$(az network public-ip show -g {rg} -n {pip} --query id -o tsv)

az network firewall allocate \
  --resource-group {rg} \
  --name {firewall-name} \
  --vnet-name {vnet} \
  --public-ip {pip}

# 6. Monitor firewall metrics
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/azureFirewalls/{name} \
  --metric "FirewallHealth,DataProcessed,SNATPortUtilization" \
  --interval PT1M
```

### Generalization
Applies to: All workloads using Azure Firewall, NVA (Network Virtual Appliance), Azure Firewall Manager. Also relevant for hub-spoke network architectures where firewall is the single egress point.

---

## Pattern AEGIS-018
**Source:** Azure WAN / Network Infrastructure — M365 Outage (January 2023)
**Priority:** HIGH

### Symptoms
- Microsoft 365 services (Teams, Outlook, SharePoint) inaccessible
- Azure services requiring Microsoft backbone connectivity degraded
- Wide-area network connectivity issues between Azure regions
- BGP routing changes visible in network monitoring
- Impact spanning multiple hours (3+ hour duration)

### Diagnosis
**Azure Wide Area Network (WAN) routing failure.** A change to Azure's WAN routing severed connectivity between the internet and Microsoft's core service infrastructure. This type of failure affects all services that route through Microsoft's backbone network, including M365 and Azure services in affected network paths.

### Root Cause Pattern
WAN configuration change → BGP routing disruption → Connectivity severed between internet and Microsoft backbone → M365 and Azure services unreachable → Rollback of WAN change required for recovery

### Remediation Script
```bash
# AEGIS-018: Azure WAN / Network Routing Failure

# 1. Verify network path to Microsoft services
traceroute outlook.office365.com
traceroute management.azure.com

# 2. Check BGP routes if using ExpressRoute
az network express-route list-route-tables \
  --resource-group {rg} \
  --circuit-name {circuit} \
  --peering-name AzurePrivatePeering \
  --path primary

# 3. Test alternative connectivity paths
# If ExpressRoute is affected, test VPN Gateway
az network vnet-gateway list-bgp-peer-status \
  --resource-group {rg} \
  --name {vpn-gateway}

# 4. For M365 — verify service connectivity
curl -I https://outlook.office365.com
curl -I https://teams.microsoft.com

# 5. If ExpressRoute is down — failover to VPN
az network vnet-gateway reset \
  --resource-group {rg} \
  --name {vpn-gateway}

# 6. Enable split tunneling as temporary measure
# For on-premise users: route M365 traffic direct to internet
# Microsoft 365 optimize endpoints: https://aka.ms/o365endpoints

# 7. Monitor network recovery
mtr --report --report-cycles 10 management.azure.com
```

### Generalization
Applies to: Organizations using ExpressRoute, Azure VPN Gateway, hybrid connectivity. Also relevant for workloads requiring Azure backbone connectivity between regions.

---

## Pattern AEGIS-019
**Source:** Azure Kubernetes Service (AKS) — Node Pool and Control Plane Issues
**Priority:** HIGH

### Symptoms
- AKS node provisioning stuck in "Creating" or "Updating" state
- kubectl commands timing out or returning connection refused
- Pods stuck in Pending state with no available nodes
- Node pool scaling operations failing
- AKS control plane API server unreachable

### Diagnosis
**AKS control plane or node pool infrastructure failure.** AKS issues typically manifest as either control plane (API server) failures affecting kubectl operations, or node pool failures preventing pod scheduling. Often caused by underlying VM infrastructure issues, network configuration problems, or Azure platform issues affecting the region.

### Root Cause Pattern
Azure VM/network infrastructure issue → AKS node provisioning fails → Pods cannot be scheduled → Services lose capacity → Scaling operations fail → Manual intervention or platform recovery required

### Remediation Script
```bash
# AEGIS-019: AKS Node Pool / Control Plane Failure

# 1. Check cluster and node status
az aks show --resource-group {rg} --name {cluster} --query "{state:provisioningState,fqdn:fqdn}"
kubectl get nodes -o wide
kubectl get pods --all-namespaces | grep -v Running

# 2. Check node pool status
az aks nodepool list \
  --resource-group {rg} \
  --cluster-name {cluster} \
  --query "[].{name:name,state:provisioningState,count:count,vmSize:vmSize}" -o table

# 3. Check control plane connectivity
kubectl cluster-info
kubectl get componentstatuses

# 4. For stuck nodes — force delete and recreate
kubectl delete node {node-name}
az aks nodepool scale \
  --resource-group {rg} \
  --cluster-name {cluster} \
  --name {nodepool} \
  --node-count {desired-count}

# 5. For control plane issues — trigger upgrade to force refresh
az aks upgrade \
  --resource-group {rg} \
  --name {cluster} \
  --kubernetes-version {current-version} \
  --node-image-only

# 6. Check for resource quota issues
az aks show --resource-group {rg} --name {cluster} \
  --query "agentPoolProfiles[].{name:name,count:count,maxCount:maxCount}"

# 7. View recent AKS events
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -30

# 8. Check node pool upgrade status
az aks nodepool show \
  --resource-group {rg} \
  --cluster-name {cluster} \
  --name {nodepool} \
  --query "{state:provisioningState,upgradeSettings:upgradeSettings}"
```

### Generalization
Applies to: All AKS workloads, Azure Container Instances, workloads on VM Scale Sets. Also relevant when AKS upgrade operations are in progress.

---

## Pattern AEGIS-020
**Source:** Azure SQL / Azure Database — Connection Pool Exhaustion and Failover
**Priority:** HIGH

### Symptoms
- Database connections failing with "connection pool exhausted" errors
- Azure SQL returning error 10928 (resource limit reached) or 40613 (database unavailable)
- Connection timeouts increasing progressively
- Read replica lag increasing dramatically
- Failover operations not completing within expected window

### Diagnosis
**Azure SQL connection pool exhaustion or geo-replication lag.** Azure SQL has per-database connection limits depending on service tier. When connection pools are exhausted — often caused by connection leaks, query pile-ups, or sudden traffic spikes — new connections are rejected. Combined with failover operations, this can create a situation where both primary and replica are degraded.

### Root Cause Pattern
Traffic spike or connection leak → Connection pool exhaustion → New connections rejected → Application retries amplify the problem → If failover triggered: replica may also be degraded due to lag or cold cache

### Remediation Script
```bash
# AEGIS-020: Azure SQL Connection Pool Exhaustion

# 1. Check current connection count
sqlcmd -S {server}.database.windows.net -d {database} -U {user} -P {password} \
  -Q "SELECT COUNT(*) as connections, status FROM sys.dm_exec_sessions GROUP BY status"

# 2. Check resource limits
sqlcmd -S {server}.database.windows.net -d {database} -U {user} -P {password} \
  -Q "SELECT * FROM sys.dm_db_resource_stats ORDER BY end_time DESC FETCH FIRST 10 ROWS ONLY"

# 3. Identify blocking queries
sqlcmd -S {server}.database.windows.net -d {database} -U {user} -P {password} \
  -Q "SELECT blocking_session_id, session_id, wait_type, wait_time, text FROM sys.dm_exec_requests CROSS APPLY sys.dm_exec_sql_text(sql_handle) WHERE blocking_session_id > 0"

# 4. Kill long-running blocking sessions
sqlcmd -S {server}.database.windows.net -d {database} -U {user} -P {password} \
  -Q "KILL {session_id}"  # Replace with actual blocking session IDs

# 5. Check geo-replication lag
az sql db replica list-links \
  --resource-group {rg} \
  --server {server} \
  --name {database} \
  --query "[].{partner:partnerServer,replicationState:replicationState,lagSeconds:replicationLagInSeconds}"

# 6. Scale up tier temporarily to increase connection limits
az sql db update \
  --resource-group {rg} \
  --server {server} \
  --name {database} \
  --service-objective S4  # Adjust to appropriate tier

# 7. Restart connection pools in application
kubectl rollout restart deployment/{app-deployment}

# 8. Monitor connection recovery
az monitor metrics list \
  --resource /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Sql/servers/{server}/databases/{db} \
  --metric "connection_successful,connection_failed,blocked_by_firewall" \
  --interval PT1M
```

### Generalization
Applies to: Azure SQL Database, Azure SQL Managed Instance, Azure Database for PostgreSQL/MySQL. Also relevant for any connection-pooled database behind a microservices layer.

---

*AEGIS Knowledge Base — Azure Patterns Extension v1.0*
*Sources: Azure Status History (azure.status.microsoft), Azure Postmortem Reviews 2022–2026*
*Total patterns after this extension: AEGIS-001 through AEGIS-020 (20 patterns)*
