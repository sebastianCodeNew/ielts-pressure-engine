# 🧪 IELTS Pressure Engine - Testing Scenarios

## 🎯 Purpose
Memastikan **semua flow berjalan normal** setelah perbaikan bug sebelumnya:
- ✅ Question mismatch (UI vs backend)
- ✅ Agent timeout (evaluasi jadi fallback)
- ✅ SignalMetrics validation error
- ✅ Frontend state synchronization

---

## 📋 Test Scenario Matrix

| Scenario | Priority | Status | Test Steps | Expected Results |
|----------|---------|--------|-------------|----------------|
| **Basic Flow** | 🔴 Critical | | | Question sync, evaluation works |
| **Retry Flow** | 🟡 High | | | Force retry works correctly |
| **Error Recovery** | 🟡 High | | | Graceful error handling |
| **Checkpoint Words** | 🟠 Medium | | | Checkpoint compliance works |
| **Audio Processing** | 🟠 Medium | | | No audio processing errors |
| **State Persistence** | 🟠 Medium | | | Session state maintained |
| **Performance** | 🟢 Low | | | Response times acceptable |

---

## 🚀 Scenario 1: Basic Exam Flow (Critical)

### 📝 Test Steps
```bash
1. Start backend (tanpa --reload untuk stability)
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000

2. Start frontend
   cd frontend
   npm run dev

3. Open browser
   http://localhost:3000

4. Start new exam
   - Click "Start Exam"
   - Verify session ID created
   - Note initial question displayed

5. Record first answer
   - Click "Start Recording"
   - Speak for 5-10 seconds
   - Click "Stop Recording"

6. Submit answer
   - Click "Submit Answer"
   - Wait for evaluation

7. Review evaluation
   - Check feedback appears
   - Check scores displayed
   - Check ideal response shown

8. Continue to next question
   - Click "Got It, Next Question"
   - Verify UI updates to new question
   - Verify new checkpoint words appear

9. Repeat steps 5-8 for second question
```

### ✅ Expected Results
```
Backend Logs:
- ✅ No "AGENT ERROR: Request timed out"
- ✅ No "SignalMetrics is_complete Field required"
- ✅ Correct prompt in logs: "--- Processing Attempt (ExamMode=True, Prompt='[actual_question]')"

Frontend Behavior:
- ✅ Question displayed matches backend prompt
- ✅ Evaluation reflects actual transcript
- ✅ Checkpoint words update correctly
- ✅ No 500 errors
- ✅ Smooth transitions between questions

Database State:
- ✅ ExamSession record created correctly
- ✅ QuestionAttempt records saved
- ✅ Checkpoint compliance calculated
- ✅ No orphaned records
```

### ❌ Failure Indicators
```
Critical Issues:
- ❌ Question mismatch between UI and backend
- ❌ Evaluation timeout with fallback
- ❌ 500 Internal Server Error
- ❌ Checkpoint words not updating
- ❌ Session state corruption

Warning Issues:
- ⚠️ Slow response (>3 seconds)
- ⚠️ High memory usage (>1GB)
- ⚠️ Whisper model reloads
- ⚠️ Database locks
```

---

## 🔄 Scenario 2: Retry Flow (High Priority)

### 📝 Test Steps
```bash
1. Start exam and go to first question

2. Record answer WITHOUT using checkpoint words
   - Intentionally skip required checkpoint words
   - Submit answer

3. Verify FORCE_RETRY triggered
   - Check "FORCE_RETRY" action_id
   - Check refactor mission appears
   - Check same question maintained

4. Record answer WITH checkpoint words
   - Use all required checkpoint words
   - Submit answer

5. Verify retry success
   - Check compliance score = 1.0
   - Check next question appears
   - Check new checkpoint words generated
```

### ✅ Expected Results
```
Retry Behavior:
- ✅ First attempt triggers FORCE_RETRY
- ✅ Same question displayed during retry
- ✅ Refactor mission clearly explains missing words
- ✅ Second attempt with checkpoint words succeeds
- ✅ Compliance score calculated correctly (words_used / words_required)

Checkpoint System:
- ✅ Required words tracked correctly
- ✅ Hit detection works (regex word boundaries)
- ✅ Compliance score calculation accurate
- ✅ New checkpoint words generated for next turn

Error Handling:
- ✅ Graceful retry without server crash
- ✅ Clear user feedback on retry reason
- ✅ No data corruption during retry
```

---

## 🚨 Scenario 3: Error Recovery (High Priority)

### 📝 Test Steps
```bash
1. Test empty audio submission
   - Record silence (0 seconds)
   - Submit

2. Test corrupted audio
   - Submit invalid audio file
   - Submit during file processing error

3. Test network interruption
   - Disconnect network during upload
   - Submit with slow connection

4. Test LLM timeout scenario
   - Submit multiple requests rapidly
   - Simulate slow LLM response

5. Test database errors
   - Lock database during operation
   - Corrupt database file
   - Fill disk space
```

### ✅ Expected Results
```
Error Handling:
- ✅ User-friendly error messages
- ✅ No server crashes (500 errors)
- ✅ Graceful degradation (read-only mode)
- ✅ Data integrity maintained
- ✅ Recovery options available

User Experience:
- ✅ Clear error explanations
- ✅ Retry options available
- ✅ No data loss
- ✅ Session can be resumed

System Stability:
- ✅ Backend remains responsive
- ✅ Other users not affected
- ✅ Logs capture error details
- ✅ Monitoring alerts triggered
```

---

## 🎯 Scenario 4: Performance & Load Testing

### 📝 Test Steps
```bash
1. Concurrent user testing
   - Start 3 simultaneous exams
   - Different user IDs
   - Monitor resource usage

2. Large audio file testing
   - Submit 2-minute audio files
   - Test with various audio formats

3. Rapid submission testing
   - Submit 10 answers in 2 minutes
   - Check for rate limiting

4. Memory leak testing
   - Monitor memory usage over time
   - Check for increasing memory consumption

5. Database performance testing
   - Query large history datasets
   - Test with 1000+ records
```

### ✅ Expected Results
```
Performance:
- ✅ Response time < 2 seconds
- ✅ Memory usage stable
- ✅ CPU usage < 80%
- ✅ No memory leaks
- ✅ Database queries efficient

Scalability:
- ✅ Handles concurrent users
- ✅ Large audio processing works
- ✅ Rate limiting effective
- ✅ Database scales with data

Monitoring:
- ✅ Performance metrics logged
- ✅ Alerts trigger for issues
- ✅ Resource usage tracked
- ✅ Bottlenecks identified
```

---

## 🔍 Scenario 5: Edge Cases (Medium Priority)

### 📝 Test Steps
```bash
1. Special characters in transcript
   - Test with emojis, unicode, accents
   - Verify processing works

2. Very long answers
   - Test 2-minute continuous speech
   - Test with filler words
   - Test with silence periods

3. Network connectivity issues
   - Slow connection simulation
   - Intermittent connection
   - Complete connection loss

4. Browser compatibility
   - Test in Chrome, Firefox, Safari
   - Test mobile responsiveness
   - Test with different screen sizes

5. Database edge cases
   - Empty database tables
   - Corrupted session IDs
   - Invalid user references
```

### ✅ Expected Results
```
Robustness:
- ✅ Special characters handled correctly
- ✅ Long audio processed without timeout
- ✅ Network issues handled gracefully
- ✅ Cross-browser compatibility
- ✅ Database constraints enforced

Data Integrity:
- ✅ No data corruption
- ✅ Validations enforced
- ✅ Edge cases handled
- ✅ Error recovery works

User Experience:
- ✅ Consistent behavior across browsers
- ✅ Helpful error messages
- ✅ Accessibility maintained
- ✅ Performance acceptable
```

---

## 📊 Test Results Template

### 📋 Daily Test Log
```
Date: 2025-02-22
Tester: [Your Name]
Environment: Development/Production
Browser: Chrome/Firefox/Safari

Scenario Results:
✅ Basic Flow - PASS
  - Question sync: ✅
  - Evaluation: ✅
  - Checkpoint words: ✅
  - No errors: ✅

❌ Retry Flow - FAIL
  - Issue: [Description]
  - Error: [Log messages]
  - Fix needed: [Action]

⚠️ Error Recovery - PARTIAL
  - Graceful handling: ✅
  - User feedback: ⚠️
  - Recovery: ✅

🟡 Performance - NEEDS ATTENTION
  - Response time: [X] seconds
  - Memory usage: [X] MB
  - Issues: [Description]

Notes:
[Additional observations]
[Bug reports or improvements needed]
```

### 🎯 Pass/Fail Criteria

#### **PASS Conditions**
- All critical scenarios pass
- No 500 errors
- Response times < 2 seconds
- Question/evaluation sync works
- Checkpoint system functional

#### **FAIL Conditions**
- Any critical scenario fails
- Server crashes or 500 errors
- Data corruption or loss
- Security vulnerabilities

#### **NEEDS ATTENTION**
- Performance degradation
- Intermittent failures
- User experience issues
- Minor bugs

---

## 🚀 Quick Test Commands

### 🧪 Run All Scenarios
```bash
# Basic functionality test
python -m pytest tests/test_scenarios.py -v

# Performance test
python tests/load_test.py --users 10 --duration 300

# Error handling test
python tests/error_scenarios.py --all

# Database integrity test
python tests/db_integrity.py --check-all
```

### 🌐 API Health Check
```bash
# Full system health
curl -X GET http://127.0.0.1:8000/api/v1/health

# Individual component checks
curl -X GET http://127.0.0.1:8000/api/v1/exams/start
curl -X GET http://127.0.0.1:8000/api/v1/users/me/stats
```

---

## 📞 Troubleshooting Guide

### 🔧 Common Issues & Solutions

#### **Issue: Questions not syncing**
```bash
Symptoms:
- UI shows different question than backend processes
- Evaluation seems unrelated to answer

Solutions:
1. Check frontend state updates
2. Verify localStorage consistency
3. Check backend prompt logging
4. Test with fresh browser session
```

#### **Issue: Evaluation timeouts**
```bash
Symptoms:
- "AGENT ERROR: Request timed out"
- Generic fallback responses
- Inconsistent evaluation quality

Solutions:
1. Check network connectivity to DeepInfra
2. Increase LLM timeout
3. Use smaller model for testing
4. Add retry logic with exponential backoff
```

#### **Issue: Audio processing failures**
```bash
Symptoms:
- 500 errors on submit
- SignalMetrics validation errors
- Whisper model issues

Solutions:
1. Check audio file formats
2. Validate SignalMetrics construction
3. Test with various audio lengths
4. Check file permissions
```

---

## ✅ Success Criteria

### 🎯 Definition of "Stable"
```
System considered stable when:
- All critical scenarios pass consistently
- No 500 errors in normal usage
- Performance within acceptable limits
- Error handling graceful and user-friendly
- Data integrity maintained
- Monitoring shows healthy metrics
```

### 📈 Continuous Monitoring
```bash
# Daily automated tests
0 6 * * * * /usr/local/bin/python3 /app/daily_tests.py

# Weekly performance review
0 0 * * 1 /usr/local/bin/python3 /app/weekly_review.py

# Monthly stability report
0 0 1 * * /usr/local/bin/python3 /app/monthly_report.py
```

---

**📌 Use this testing guide daily to ensure system stability!**

**Last Updated**: 2025-02-22
**Version**: 1.0
**Status**: Active Testing
