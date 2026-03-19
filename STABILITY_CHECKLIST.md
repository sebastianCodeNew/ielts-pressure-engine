# 🛡️ IELTS Pressure Engine - Stability Checklist

## 📋 Pre-Start Validation (Sebelum Start Backend)

### 🔍 Environment Check
- [ ] **Virtual Environment Active**
  ```bash
  # Pastikan venv aktif
  echo $VIRTUAL_ENV
  # Harusnya: backend/venv
  ```

- [ ] **Dependencies Valid**
  ```bash
  # Cek critical dependencies
  pip list | grep -E "(langchain|openai|whisper|fastapi|uvicorn)"
  ```

- [ ] **Environment Variables Set**
  ```bash
  # Cek .env variables
  cat .env | grep -E "(DEEPINFRA|DATABASE|API)"
  ```

- [ ] **Port Available**
  ```bash
  # Cek port 8000 tidak dipakai
  netstat -an | grep 8000
  ```

### 🗄️ Database Check
- [ ] **Database File Exists**
  ```bash
  # Cek file database
  ls -la backend/app.db
  ```

- [ ] **Database Permissions**
  ```bash
  # Cek write permissions
  touch backend/test_write.tmp && rm backend/test_write.tmp
  ```

- [ ] **Migration Status**
  ```bash
  # Cek migrasi sudah jalan
  python -c "from app.core.database import engine; print('DB OK')"
  ```

---

## 🚀 Startup Validation (Saat Start Backend)

### ✅ Healthy Startup Indicators
- [ ] **Whisper Model Loads Once**
  ```
  ✅ Expected: --- Loading Whisper Model (medium.en) ---
  ✅ Expected: --- Whisper Model Loaded ---
  ❌ Warning: Multiple loads atau load gagal
  ```

- [ ] **Database Migrates Cleanly**
  ```
  ✅ Expected: --- Database Schema Verified & Migrated ---
  ❌ Error: Migration errors atau table creation gagal
  ```

- [ ] **API Server Starts**
  ```
  ✅ Expected: INFO: Uvicorn running on http://127.0.0.1:8000
  ❌ Error: Port bind failed atau address already in use
  ```

### ⚠️ Common Startup Issues & Solutions

#### **Issue 1: Port Already in Use**
```bash
# Symptom:
ERROR: [Errno 98] Address already in use

# Solution:
netstat -ano | grep 8000
# Kill process:
taskkill /PID <PID> /F
# Atau ganti port:
uvicorn app.main:app --port 8001
```

#### **Issue 2: Whisper Model Corrupted**
```bash
# Symptom:
ERROR: Failed to load whisper model

# Solution:
# Download ulang model
python -c "import whisper; whisper.load_model('medium.en')"
```

#### **Issue 3: Database Locked**
```bash
# Symptom:
sqlite3.OperationalError: database is locked

# Solution:
# Hapus lock file
rm backend/app.db-journal
# Atau restart service
```

---

## 🔄 Runtime Validation (Saat Backend Berjalan)

### 📊 Health Checks
- [ ] **API Endpoint Responsive**
  ```bash
  curl -f http://127.0.0.1:8000/api/v1/exams/start
  # Expected: 200 OK atau error JSON yang valid
  ```

- [ ] **Database Connection Stable**
  ```bash
  # Test query
  curl -f http://127.0.0.1:8000/api/v1/users/me/stats
  ```

- [ ] **Memory Usage Reasonable**
  ```bash
  # Monitor memory
  tasklist | grep python
  # Warning: > 1GB memory usage
  ```

### 🐛 Common Runtime Issues & Solutions

#### **Issue 1: LLM Timeout**
```python
# Symptom:
AGENT ERROR: Request timed out.

# Solutions:
# 1. Increase timeout (sudah dilakukan)
timeout=90  # seconds

# 2. Check internet connection
ping deepinfra.com

# 3. Use smaller model
EVALUATOR_MODEL="meta-llama/Meta-Llama-3-8B-Instruct"

# 4. Add retry logic
max_retries=3
retry_delay=5
```

#### **Issue 2: Frontend-Backend Mismatch**
```javascript
// Symptom:
// UI shows: "Tell me about your family"
// Backend processes: "What kind of music do you like?"

// Solutions:
// 1. Ensure feedback state updates
setFeedback(prev => ({
  ...prev,
  next_task_prompt: newPrompt
}));

// 2. Clear stale localStorage
localStorage.removeItem('ielts_exam_session_id');

// 3. Refresh page setelah major changes
window.location.reload();
```

#### **Issue 3: Audio Processing Failures**
```python
# Symptom:
Error processing exam audio: 1 validation error for SignalMetrics

# Solutions:
# 1. Ensure SignalMetrics complete
SignalMetrics(
    fluency_wpm=67.6,
    hesitation_ratio=0.2,
    is_complete=True,  # ← Critical!
    # ... other fields
)

# 2. Add validation before processing
if not attempt.transcript or len(attempt.transcript.split()) < 2:
    return Intervention(action_id="FORCE_RETRY", ...)

# 3. Graceful error handling
try:
    result = process_audio(file_path)
except Exception as e:
    logger.error(f"Audio processing failed: {e}")
    return Intervention(action_id="MAINTAIN", ...)
```

---

## 🧪 Testing Scenarios (Wajib Dicoba)

### 📝 Scenario 1: Basic Exam Flow
```bash
# Test steps:
1. Start backend: uvicorn app.main:app --reload
2. Start frontend: npm run dev
3. Open browser: http://localhost:3000
4. Click "Start Exam"
5. Record audio (5-10 seconds)
6. Submit audio
7. Check evaluation appears
8. Click "Got It, Next Question"
9. Verify UI updates correctly

# Expected results:
✅ Question matches between UI and backend
✅ Evaluation reflects actual transcript
✅ No 500 errors
✅ Checkpoint words work
```

### 🔄 Scenario 2: Retry Flow
```bash
# Test steps:
1. Submit audio with missing checkpoint words
2. Verify "FORCE_RETRY" triggered
3. Record new audio with correct words
4. Verify retry succeeds
5. Check checkpoint compliance score

# Expected results:
✅ Force retry works correctly
✅ Same question maintained during retry
✅ Checkpoint compliance calculated correctly
```

### 🚨 Scenario 3: Error Recovery
```bash
# Test steps:
1. Submit empty audio
2. Submit corrupted audio
3. Disconnect network during submit
4. Submit during LLM timeout

# Expected results:
✅ Graceful error messages
✅ No server crashes
✅ User can retry successfully
✅ Data integrity maintained
```

---

## 🔧 Development Best Practices

### 📝 Code Changes
- [ ] **Test changes locally before commit**
- [ ] **Add error handling for new features**
- [ ] **Update tests for new functionality**
- [ ] **Document breaking changes**

### 🗄️ Database Operations
- [ ] **Use transactions for multi-table operations**
- [ ] **Add foreign key constraints**
- [ ] **Implement data validation**
- [ ] **Backup database before major changes**

### 🌐 API Design
- [ ] **Validate input schemas**
- [ ] **Add rate limiting**
- [ ] **Implement proper HTTP status codes**
- [ ] **Add API versioning**

### 🎯 Frontend Integration
- [ ] **Handle loading states**
- [ ] **Add error boundaries**
- [ ] **Implement offline detection**
- [ ] **Add responsive design checks**

---

## 📊 Monitoring & Logging

### 📈 Performance Metrics
```python
# Monitor these metrics:
- Response time < 2 seconds
- Memory usage < 1GB
- CPU usage < 80%
- Error rate < 1%
- LLM timeout rate < 5%
```

### 📝 Log Levels
```python
# Development:
DEBUG - Detailed information for debugging

# Production:
INFO - General information
WARNING - Potential issues
ERROR - Actual errors
CRITICAL - System failures
```

### 🚨 Alert Thresholds
```bash
# Alert jika:
- Memory > 1.5GB
- CPU > 90% for 30 seconds
- Error rate > 2%
- LLM timeout > 10% of requests
- Database response time > 1 second
```

---

## ✅ Pre-Deployment Checklist

### 🔍 Final Validation
- [ ] **All tests pass**
- [ ] **No console errors**
- [ ] **Performance acceptable**
- [ ] **Security scan passed**
- [ ] **Documentation updated**

### 🚀 Deployment Steps
```bash
# 1. Clean build
rm -rf .next
rm -rf node_modules/.cache

# 2. Install dependencies
npm ci
pip install -r requirements.txt

# 3. Run production server
uvicorn app.main:app --workers 4

# 4. Health check
curl -f http://localhost:8000/health
```

---

## 🆘 Emergency Procedures

### 🚨 Server Down
```bash
# Quick restart:
pkill -f uvicorn
uvicorn app.main:app --reload

# Check logs:
tail -f logs/uvicorn.log
```

### 🗄️ Database Corruption
```bash
# Backup current:
cp backend/app.db backend/app.db.backup.$(date +%Y%m%d)

# Restore from backup:
cp backend/app.db.backup.20250222 backend/app.db
```

### 🔐 Security Issues
```bash
# Change API keys:
# Update .env file
# Restart services
# Rotate secrets
```

---

## 📞 Contact & Escalation

### 🐛 Bug Report Template
```
Environment: Development/Production
Browser: Chrome/Firefox/Safari
User ID: [user_id]
Session ID: [session_id]
Timestamp: [YYYY-MM-DD HH:MM:SS]

Issue Description:
[Detailed description]

Steps to Reproduce:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Expected Behavior:
[What should happen]

Actual Behavior:
[What actually happened]

Error Messages:
[Copy-paste error logs]

Workaround:
[Temporary fix if any]
```

### 📞 Emergency Contacts
- **Technical Lead**: [contact info]
- **System Administrator**: [contact info]
- **Database Administrator**: [contact info]

---

## ✅ Usage Instructions

### 📋 Daily Development
1. **Morning**: Run through this checklist
2. **Before commits**: Validate all scenarios
3. **After major changes**: Full testing suite
4. **Weekly**: Review and update checklist

### 🎯 Critical Situations
- **Production issues**: Use Production checklist
- **Security incidents**: Follow Security procedures
- **Data corruption**: Emergency procedures
- **Performance degradation**: Monitoring alerts

---

**📌 Save this checklist and review daily!**

**Last Updated**: 2025-02-22
**Version**: 1.0
**Status**: Active
