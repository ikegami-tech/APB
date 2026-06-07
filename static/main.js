// --- 画面遷移の処理 ---
function goToStep2() {
    const propType = document.getElementById('property-type').value;
    if (!propType) {
        alert('🚨 物件種別（マンションか戸建て）を選択してください！');
        return;
    }
    document.getElementById('step-1-property').classList.add('hidden');
    document.getElementById('step-2-design').classList.remove('hidden');
}

function goBackToStep1() {
    document.getElementById('step-2-design').classList.add('hidden');
    document.getElementById('step-1-property').classList.remove('hidden');
}

function goToEditor(designNum) {
    const propType = document.getElementById('property-type').value;
    document.getElementById('editor-subtitle').innerText = `🎨 編集画面（${propType} / デザイン ${designNum}）`;
    document.getElementById('step-2-design').classList.add('hidden');
    document.getElementById('step-3-editor').classList.remove('hidden');
}

function goBackToStep2() {
    document.getElementById('step-3-editor').classList.add('hidden');
    document.getElementById('step-2-design').classList.remove('hidden');
}

// --- モーダルと通信処理 ---
function openModal(id) { document.getElementById(id).style.display = 'block'; }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

async function sendDataToPython(formData) {
    try {
        const response = await fetch("http://127.0.0.1:8000/generate_zumen", { method: "POST", body: formData });
        const result = await response.json();
        console.log("Pythonからの返事:", result.message);
    } catch (error) { console.error("通信エラー", error); }
}

function saveTitle() {
    const newTitle = document.getElementById('input-title').value;
    document.getElementById('display-title').innerText = newTitle;
    closeModal('titleModal');
    const formData = new FormData();
    formData.append("title", newTitle);
    sendDataToPython(formData);
}

function saveInfo() {
    document.getElementById('display-price').innerText = document.getElementById('input-price').value;
    document.getElementById('display-address').innerText = document.getElementById('input-address').value;
    closeModal('infoModal');
}

async function saveImage() {
    const file = document.getElementById('input-image').files[0];
    if (file) {
        document.getElementById('display-image').src = URL.createObjectURL(file);
        document.getElementById('display-image').classList.remove('hidden');
        document.getElementById('image-placeholder-icon').classList.add('hidden');
        document.getElementById('image-placeholder-text').classList.add('hidden');
        document.getElementById('image-preview-area').style.backgroundColor = 'transparent';
        
        const formData = new FormData();
        formData.append("title", document.getElementById('display-title').innerText);
        formData.append("madori_image", file);
        await sendDataToPython(formData);
    }
    closeModal('imageModal');
}

async function downloadPptx() {
    const btn = document.querySelector('button[onclick="downloadPptx()"]');
    const originalText = btn.innerText;
    btn.innerText = "⏳ パワポを作成中...";
    btn.disabled = true;
    try {
        const formData = new FormData();
        formData.append("title", document.getElementById('display-title').innerText);
        formData.append("price", document.getElementById('display-price').innerText);
        formData.append("address", document.getElementById('display-address').innerText);
        const file = document.getElementById('input-image').files[0];
        if (file) formData.append("main_image", file);

        const response = await fetch("http://127.0.0.1:8000/generate_zumen_file", { method: "POST", body: formData });
        if (!response.ok) throw new Error("サーバーエラー");

        const blob = await response.blob();
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = `販売図面_${formData.get("title")}.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(a.href);
    } catch (error) {
        alert("⚠️ 作成中にエラーが発生しました。");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}
// ==========================================
// APB（パンフレット自動作成）用の処理
// ==========================================
async function startApbGeneration() {
    const btn = document.querySelector('.btn-apb-generate');
    const originalText = btn.innerText;
    btn.innerText = "⏳ 通信テスト中...";
    btn.disabled = true;

    // 画面に入力されたファイルや設定を集める箱
    const formData = new FormData();
    
    const zumen = document.getElementById('apb-zumen').files[0];
    const madori = document.getElementById('apb-madori').files[0];
    const empty = document.getElementById('apb-empty').files[0];
    const map = document.getElementById('apb-map').files[0];
    
    if(zumen) formData.append("zumen_file", zumen);
    if(madori) formData.append("madori_file", madori);
    if(empty) formData.append("empty_file", empty);
    if(map) formData.append("map_file", map);

    const orientation = document.querySelector('input[name="apb_orientation"]:checked').value;
    formData.append("orientation", orientation);

    try {
        const response = await fetch("http://127.0.0.1:8000/generate_apb", { 
            method: "POST", 
            body: formData 
        });
        
        const result = await response.json();
        alert(result.message);
        
    } catch (error) {
        alert("⚠️ 通信エラーが発生しました。サーバーが起動しているか確認してください。");
        console.error(error);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}