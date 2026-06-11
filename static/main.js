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
    const statusDiv = document.getElementById('progress-status');
    const previewSection = document.getElementById('apb-preview-section');
    const previewContainer = document.getElementById('apb-preview-images');
    const originalText = btn.innerText;

    // 前回のプレビューや状態をリセット
    previewSection.classList.add('hidden');
    previewContainer.innerHTML = "";
    window.generatedPptxBase64 = null;

    btn.innerText = "⏳ パンフレットを作成中...";
    btn.disabled = true;
    statusDiv.innerText = "🚀 処理を開始しています...";

    const formData = new FormData();
    const zumen = document.getElementById('apb-zumen').files[0];
    const madori = document.getElementById('apb-madori').files[0];
    const empty = document.getElementById('apb-empty').files[0];
    
    // 🌟 修正：地図枠が削除されていてもエラーを出さずにスキップする安全処理
    const mapElement = document.getElementById('apb-map');
    const map = mapElement ? mapElement.files[0] : null;
    
    if(zumen) formData.append("zumen_file", zumen);
    if(madori) formData.append("madori_file", madori);
    if(empty) formData.append("empty_file", empty);
    if(map) formData.append("map_file", map);

    const orientation = document.querySelector('input[name="apb_orientation"]:checked').value;
    formData.append("orientation", orientation);

    const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]');
    const pageOptions = ["cover", "aerial_map", "access", "floor_plan", "interior_hq", "interior", "company"];
    checkboxes.forEach((chk, index) => {
        if (chk.checked) {
            formData.append("selected_pages", pageOptions[index]);
        }
    });

    const progressMessages = [
        "🔍 販売図面をAI（OCR）で読み取り中...\nしばらくお待ちください。",
        "🧠 AIが物件情報、地域名、デザインテーマを詳細分析中...",
        "📸 表紙のデザイン案を3パターン同時にImagenで生成中...\n（これには約15〜30秒かかります）",
        "🗺️ 地図画像をネイビー＆ゴールドの高級仕様に変換中...",
        "🎨 内観完成予想イメージをAI家具合成で生成中...",
        "📊 高級感のあるPowerPointスライドを1枚ずつ緻密に組み立て中..."
    ];
    
    let msgIndex = 0;
    statusDiv.innerText = progressMessages[msgIndex];
    
    const progressTimer = setInterval(() => {
        if (msgIndex < progressMessages.length - 1) {
            msgIndex++;
            statusDiv.innerText = progressMessages[msgIndex];
        }
    }, 12000);

    try {
        const response = await fetch("http://127.0.0.1:8000/generate_apb", { 
            method: "POST", 
            body: formData 
        });
        
        if (!response.ok) throw new Error("サーバーエラーが発生しました");
        
        clearInterval(progressTimer);
        statusDiv.innerText = "✨ パワポファイルの組み立てが完了しました！";
        
        // 🌟 バイナリではなくJSONデータ（画像リストとパワポデータ）として受け取る
        const result = await response.json();
        
        // パワポのデータとファイル名をメモリ（ブラウザ）に一時保存
        window.generatedPptxBase64 = result.pptx_base64;
        window.generatedPamphletFileName = zumen ? `パンフレット_${zumen.name.split('.')[0]}.pptx` : 'パンフレット_自動生成.pptx';

        // 🌟 画面上にプレビュー画像をずらりと並べる（Streamlitの挙動を完全再現）
        result.preview_images.forEach(item => {
            const card = document.createElement('div');
            card.style = "background: white; border: 1px solid #CFD8DC; border-radius: 6px; padding: 12px; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.05); width: 190px;";
            
            const label = document.createElement('div');
            label.style = "font-weight: bold; font-size: 13px; color: #1E2D3D; margin-bottom: 8px; text-transform: uppercase; border-bottom: 1px solid #E4E7EB; padding-bottom: 4px;";
            label.innerText = item.type;
            
            const img = document.createElement('img');
            // 🌟 png から jpeg に変更して、軽量化された画像と同期させます
            img.src = "data:image/jpeg;base64," + item.image;
            img.style = "width: 100%; height: auto; border: 1px solid #E4E7EB; border-radius: 4px;";
            
            card.appendChild(label);
            card.appendChild(img);
            previewContainer.appendChild(card);
        });

        // プレビューエリアをスッと表示
        previewSection.classList.remove('hidden');
        alert("🎉 パンフレットの生成が完了しました！下部のプレビューを確認して保存してください。");
        statusDiv.innerText = "";
        
    } catch (error) {
        clearInterval(progressTimer);
        alert("⚠️ 生成中にエラーが発生しました。");
        statusDiv.innerText = "❌ エラーが発生したため処理を中断しました。";
        console.error(error);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// 📥 保存ボタンが押された時にパワポファイルをダウンロードさせる新規関数
function downloadGeneratedPamphlet() {
    if (!window.generatedPptxBase64) {
        alert("⚠️ 保存するデータが見つかりません。もう一度生成し直してください。");
        return;
    }
    // Base64からデータバイナリ（Blob）へデコード変換
    const byteCharacters = atob(window.generatedPptxBase64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], {type: "application/vnd.openxmlformats-officedocument.presentationml.presentation"});
    
    const a = document.createElement('a');
    a.href = window.URL.createObjectURL(blob);
    a.download = window.generatedPamphletFileName;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(a.href);
}