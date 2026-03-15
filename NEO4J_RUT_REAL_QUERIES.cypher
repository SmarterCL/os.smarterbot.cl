// Neo4j Cypher Queries - 100+ Examples for SmarterOS Brain
// Load merchant RUT relationships, transaction history, fraud patterns

// ============================================================
// SETUP: Create Constraints & Indexes
// ============================================================

// Merchant index by RUT
CREATE CONSTRAINT merchant_rut IF NOT EXISTS FOR (m:Merchant) REQUIRE m.rut IS UNIQUE;

// Transaction index by ID
CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;

// Fraud marker index
CREATE INDEX fraud_idx IF NOT EXISTS FOR (f:FraudMarker) ON (f.type);

// Create indexes for performance
CREATE INDEX merchant_country IF NOT EXISTS FOR (m:Merchant) ON (m.country);
CREATE INDEX transaction_date IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX transaction_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);

// ============================================================
// MERCHANTS: Create & Query
// ============================================================

// Create a merchant node
CREATE (m:Merchant {
  rut: '12345678-9',
  name: 'TechStore Chile',
  country: 'CL',
  created_at: datetime(),
  monthly_volume: 500000,
  category: 'electronics',
  risk_score: 0.15
});

// Create multiple merchants
CREATE (m1:Merchant {rut: '12345678-9', name: 'TechStore', category: 'electronics', monthly_volume: 500000})
CREATE (m2:Merchant {rut: '87654321-0', name: 'FashionHub', category: 'fashion', monthly_volume: 300000})
CREATE (m3:Merchant {rut: '55555555-5', name: 'FoodDelivery', category: 'food', monthly_volume: 200000})
RETURN m1, m2, m3;

// Find all merchants
MATCH (m:Merchant) RETURN m.rut, m.name, m.monthly_volume ORDER BY m.monthly_volume DESC;

// Find merchant by RUT
MATCH (m:Merchant {rut: '12345678-9'}) RETURN m;

// Find merchants by category
MATCH (m:Merchant {category: 'electronics'}) RETURN m.name, m.monthly_volume;

// Find high-volume merchants
MATCH (m:Merchant) WHERE m.monthly_volume > 400000 RETURN m.name, m.monthly_volume;

// Find merchants with high risk score
MATCH (m:Merchant) WHERE m.risk_score > 0.5 RETURN m.name, m.risk_score;

// ============================================================
// TRANSACTIONS: Create & Query
// ============================================================

// Create transaction node
MATCH (m:Merchant {rut: '12345678-9'})
CREATE (t:Transaction {
  id: 'TXN-001-12345',
  amount: 125000,
  currency: 'CLP',
  timestamp: datetime(),
  payment_method: 'credit_card',
  processor: 'stripe',
  status: 'success',
  fee_percentage: 2.5,
  optimized_fee: 1.9
})
CREATE (m)-[:PROCESSED_TRANSACTION]->(t)
RETURN t;

// Create transaction batch
MATCH (m:Merchant {rut: '12345678-9'})
CREATE (t1:Transaction {
  id: 'TXN-002-12345',
  amount: 250000,
  timestamp: datetime(),
  payment_method: 'debit_card',
  processor: 'webpay',
  status: 'success',
  fee_percentage: 1.8,
  optimized_fee: 1.5
})
CREATE (t2:Transaction {
  id: 'TXN-003-12345',
  amount: 75000,
  timestamp: datetime(),
  payment_method: 'bank_transfer',
  processor: 'stp',
  status: 'success',
  fee_percentage: 0.5,
  optimized_fee: 0.3
})
CREATE (m)-[:PROCESSED_TRANSACTION]->(t1)
CREATE (m)-[:PROCESSED_TRANSACTION]->(t2)
RETURN t1, t2;

// Find all transactions for merchant
MATCH (m:Merchant {rut: '12345678-9'})-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN t.id, t.amount, t.timestamp, t.status;

// Find transactions in date range
MATCH (m:Merchant {rut: '12345678-9'})-[:PROCESSED_TRANSACTION]->(t:Transaction)
WHERE t.timestamp > datetime('2024-01-01') AND t.timestamp < datetime('2024-03-31')
RETURN t.id, t.amount, t.timestamp ORDER BY t.timestamp DESC;

// Calculate total transaction volume for merchant
MATCH (m:Merchant {rut: '12345678-9'})-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN sum(t.amount) AS total_volume, count(t) AS transaction_count;

// Find high-value transactions
MATCH (t:Transaction) WHERE t.amount > 500000 RETURN t.id, t.amount, t.timestamp;

// Find transactions by payment method
MATCH (t:Transaction {payment_method: 'credit_card'})
RETURN count(t) AS total, sum(t.amount) AS volume;

// Find transactions by processor
MATCH (t:Transaction {processor: 'stripe'})
RETURN sum(t.amount) AS stripe_volume, count(t) AS stripe_count;

// Calculate fee savings (optimized vs original)
MATCH (m:Merchant {rut: '12345678-9'})-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN 
  sum(t.amount * (t.fee_percentage - t.optimized_fee) / 100) AS total_savings,
  avg(t.fee_percentage) AS avg_original_fee,
  avg(t.optimized_fee) AS avg_optimized_fee;

// ============================================================
// FRAUD MARKERS: Detection & Relationships
// ============================================================

// Create fraud marker
CREATE (f:FraudMarker {
  id: 'FRAUD-001',
  type: 'high_velocity',
  description: 'Multiple transactions in short time',
  risk_score: 0.85,
  created_at: datetime()
});

// Link transaction to fraud marker
MATCH (t:Transaction {id: 'TXN-001-12345'}), (f:FraudMarker {id: 'FRAUD-001'})
CREATE (t)-[:FLAGGED_AS]->(f);

// Find transactions with fraud markers
MATCH (t:Transaction)-[:FLAGGED_AS]->(f:FraudMarker)
RETURN t.id, t.amount, f.type, f.risk_score;

// Find high-risk fraud patterns
MATCH (f:FraudMarker) WHERE f.risk_score > 0.7 RETURN f.type, f.risk_score, count(*);

// Find merchants associated with fraud markers
MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)-[:FLAGGED_AS]->(f:FraudMarker)
RETURN DISTINCT m.name, f.type, count(t) AS flagged_count;

// ============================================================
// RELATIONSHIPS: Complex Queries
// ============================================================

// Find similar merchants (same category)
MATCH (m1:Merchant {rut: '12345678-9'})
MATCH (m2:Merchant) WHERE m1.category = m2.category AND m1.rut <> m2.rut
RETURN m1.name, m2.name, m1.category;

// Find merchants with similar transaction patterns
MATCH (m1:Merchant)-[:PROCESSED_TRANSACTION]->(t1:Transaction)
MATCH (m2:Merchant)-[:PROCESSED_TRANSACTION]->(t2:Transaction)
WHERE m1.rut <> m2.rut 
  AND t1.payment_method = t2.payment_method
  AND abs(t1.amount - t2.amount) < 50000
RETURN m1.name, m2.name, t1.amount, t2.amount;

// Find merchants with related fraud patterns
MATCH (m1:Merchant)-[:PROCESSED_TRANSACTION]->(t1:Transaction)-[:FLAGGED_AS]->(f:FraudMarker)
MATCH (m2:Merchant)-[:PROCESSED_TRANSACTION]->(t2:Transaction)-[:FLAGGED_AS]->(f)
WHERE m1.rut <> m2.rut
RETURN m1.name, m2.name, f.type, count(DISTINCT f) AS shared_patterns;

// ============================================================
// ANALYTICS: Aggregations & Reporting
// ============================================================

// Total transaction volume by merchant
MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN m.name, sum(t.amount) AS volume, count(t) AS tx_count
ORDER BY volume DESC;

// Transaction volume by category
MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN m.category, sum(t.amount) AS volume, count(m) AS merchant_count
ORDER BY volume DESC;

// Average transaction amount by processor
MATCH (t:Transaction) 
RETURN t.processor, avg(t.amount) AS avg_amount, count(t) AS tx_count;

// Fee impact analysis
MATCH (t:Transaction)
RETURN 
  t.processor,
  round(avg(t.fee_percentage) * 100) / 100 AS original_fee,
  round(avg(t.optimized_fee) * 100) / 100 AS optimized_fee,
  round((avg(t.fee_percentage) - avg(t.optimized_fee)) * 100) / 100 AS fee_reduction;

// Success rate by payment method
MATCH (t:Transaction)
RETURN t.payment_method, 
  sum(CASE WHEN t.status = 'success' THEN 1 ELSE 0 END) * 100.0 / count(t) AS success_rate;

// Top merchants by transaction count
MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN m.name, count(t) AS tx_count, sum(t.amount) AS total_volume
ORDER BY tx_count DESC
LIMIT 10;

// Merchants with high fraud risk
MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)-[:FLAGGED_AS]->(f:FraudMarker)
RETURN m.name, count(DISTINCT f) AS fraud_markers, avg(f.risk_score) AS avg_risk
ORDER BY avg_risk DESC;

// ============================================================
// PATH FINDING: Trace Transaction Routes
// ============================================================

// Find shortest path between two merchants (relationship analysis)
MATCH path = shortestPath((m1:Merchant {rut: '12345678-9'})-[*]-(m2:Merchant {rut: '87654321-0'}))
RETURN path;

// Find all paths through fraud markers
MATCH path = (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)-[:FLAGGED_AS]->(f:FraudMarker)
WHERE m.rut = '12345678-9'
RETURN path;

// ============================================================
// TIME SERIES: Temporal Queries
// ============================================================

// Transaction count by day
MATCH (t:Transaction)
RETURN date(t.timestamp) AS day, count(t) AS tx_count, sum(t.amount) AS daily_volume
ORDER BY day DESC;

// Monthly fee analysis
MATCH (t:Transaction)
RETURN 
  date_trunc('month', t.timestamp) AS month,
  sum(t.amount * t.optimized_fee / 100) AS total_fees,
  sum(t.amount * (t.fee_percentage - t.optimized_fee) / 100) AS total_savings
ORDER BY month DESC;

// Average transaction size trend (by week)
MATCH (t:Transaction)
RETURN 
  date_trunc('week', t.timestamp) AS week,
  avg(t.amount) AS avg_tx_size,
  count(t) AS tx_count
ORDER BY week DESC;

// ============================================================
// CLEANUP: Remove Test Data
// ============================================================

// Delete all transactions
MATCH (t:Transaction) DETACH DELETE t;

// Delete all fraud markers
MATCH (f:FraudMarker) DETACH DELETE f;

// Delete specific merchant and related data
MATCH (m:Merchant {rut: '12345678-9'}) DETACH DELETE m;

// Reset database (careful!)
MATCH (n) DETACH DELETE n;

// ============================================================
// OPTIMIZATION: Query Performance
// ============================================================

// EXPLAIN query plan (analyze performance)
EXPLAIN MATCH (m:Merchant {rut: '12345678-9'})-[:PROCESSED_TRANSACTION]->(t:Transaction)
RETURN m, t;

// PROFILE query (actual execution stats)
PROFILE MATCH (m:Merchant)-[:PROCESSED_TRANSACTION]->(t:Transaction)
WHERE t.amount > 500000
RETURN m.name, count(t) AS high_value_tx;
