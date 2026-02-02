// Node 22+ uses global fetch
async function testFrontendAPI() {
    console.log("🚀 STARTING FRONTEND API CONTRACT TEST\n");
    const BASE_URL = "http://127.0.0.1:8000/api/v1";
    const TEST_USER = "frontend_test_user";

    try {
        console.log("[1] Testing Start Exam Endpoint...");
        const startRes = await fetch(`${BASE_URL}/exams/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: TEST_USER, exam_type: 'FULL_MOCK' })
        });
        
        if (startRes.status === 200) {
            const data = await startRes.json();
            console.log(`✅ Success: Session ${data.id} created.`);
            console.log(`✅ Briefing: ${data.briefing_text.substring(0, 50)}...`);
        } else {
            console.error(`❌ Failed: ${startRes.status} ${await startRes.text()}`);
        }

        console.log("\n[2] Testing Vocabulary Fetch...");
        const vocabRes = await fetch(`${BASE_URL}/vocabulary/`);
        if (vocabRes.status === 200) {
            console.log("✅ Success: Vocabulary list retrieved.");
        } else {
             console.error(`❌ Failed: ${vocabRes.status}`);
        }

        console.log("\n[3] Testing Practice topics...");
        const topicRes = await fetch(`${BASE_URL}/practice/topics`);
        if (topicRes.status === 200) {
            console.log("✅ Success: Topics retrieved.");
        } else {
             console.error(`❌ Failed: ${topicRes.status}`);
        }

    } catch (e) {
        console.error("❌ Test crashed:", e.message);
    }
}
testFrontendAPI();
