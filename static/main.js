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
        const response = await fetch("/generate_zumen", { method: "POST", body: formData });
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

        const response = await fetch("/generate_zumen_file", { method: "POST", body: formData });
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
// APB（パンフレット自動作成）用の処理（詳細ログ＆エラー表示版）
// ==========================================
async function startApbGeneration() {
    const btn = document.querySelector('.btn-apb-generate') || document.querySelector('button[onclick="startApbGeneration()"]');
    const statusDiv = document.getElementById('progress-status');
    const subStatusDiv = document.getElementById('progress-sub-status'); // 新設枠
    const errorBox = document.getElementById('error-log-box');           // 新設枠
    const errorText = document.getElementById('error-log-text');         // 新設枠
    const previewSection = document.getElementById('apb-preview-section');
    const previewContainer = document.getElementById('apb-preview-images');
    const originalText = btn.innerText;

    // 前回の表示をすべてリセット
    previewSection.classList.add('hidden');
    previewContainer.innerHTML = "";
    if (errorBox) errorBox.classList.add('hidden'); // エラー枠を隠す
    if (subStatusDiv) subStatusDiv.style.display = 'block'; // サブ枠を表示
    window.generatedPptxBase64 = null;

    btn.innerText = "⏳ パンフレットを作成中...";
    btn.disabled = true;
    statusDiv.innerText = "🚀 処理を開始しています...";

    const formData = new FormData();
    const zumen = document.getElementById('apb-zumen').files[0];
    const madori = document.getElementById('apb-madori').files[0];
    const empty = document.getElementById('apb-empty').files[0];
    const mapElement = document.getElementById('apb-map');
    const map = mapElement ? mapElement.files[0] : null;

    if(zumen) formData.append("zumen_file", zumen);
    if(madori) formData.append("madori_file", madori);
    if(empty) formData.append("empty_file", empty);
    if(map) formData.append("map_file", map);

    const orientationElement = document.querySelector('input[name="apb_orientation"]:checked');
    const orientation = orientationElement ? orientationElement.value : 'portrait';
    formData.append("orientation", orientation);

    const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]');
    const pageOptions = ["cover", "aerial_map", "access", "floor_plan", "interior_hq", "interior", "company"];
    checkboxes.forEach((chk, index) => {
        if (chk && chk.checked) {
            formData.append("selected_pages", pageOptions[index]);
        }
    });

    // 🌟 ユーザーを退屈させないためのステップ進捗メッセージ
    const progressSteps = [
        { main: "🔍 販売図面をAI（OCR）で読み取り中...", sub: "💡 画像から物件の文字情報をスキャンしています（約15秒）" },
        { main: "🧠 AIが物件情報、地域名、デザインテーマを詳細分析中...", sub: "💡 キャッチコピーや、物件に最適なカラーを選定しています" },
        { main: "📸 表紙のデザイン案を3パターン同時にImagenで生成中...", sub: "💡 高級ホテルのようなリビング・外観イメージをAIが描いています（約30秒）" },
        { main: "🗺️ 地図画像をネイビー＆ゴールドの高級仕様に変換中...", sub: "💡 案内地図をおしゃれなパンフレット用デザインに自動加工しています" },
        { main: "🎨 内観完成予想イメージをAI家具合成で生成中...", sub: "💡 空室写真にバーチャルステージングを施し、家具を配置しています" },
        { main: "🏛️ 会社案内と周辺環境データのドキュメントを結合中...", sub: "💡 東宝ハウスの紹介ページと、地域の統計データをまとめています" },
        { main: "📊 高級感のあるPowerPointスライドを1枚ずつ緻密に組み立て中...", sub: "💡 仕上げ段階です。文字と画像をパワポ形式に高精度で合成しています" }
    ];

    let currentStep = 0;
    statusDiv.innerText = progressSteps[currentStep].main;
    if (subStatusDiv) subStatusDiv.innerText = progressSteps[currentStep].sub;
    
// 💡 より確実な非同期処理によるメッセージの切り替え
    let isGenerating = true; // 生成処理中かどうかのフラグ

    const updateProgress = async () => {
        for (let i = 0; i < progressSteps.length; i++) {
            if (!isGenerating) break; // 生成処理が終わっていたらループを抜ける
            
            statusDiv.innerText = progressSteps[i].main;
            if (subStatusDiv) subStatusDiv.innerText = progressSteps[i].sub;
            
            // 次のメッセージに切り替わるまで10秒待機 (最後のメッセージは待機しない)
            if (i < progressSteps.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 10000));
            }
        }
    };

    // メッセージの切り替えを開始 (非同期で実行)
    updateProgress();

    try {
        const response = await fetch("/generate_apb", { method: "POST", body: formData });
        
        isGenerating = false; // 生成処理が終わったのでフラグをオフにする
        
        if (!response.ok) {
            // ステータスコードが504（Gateway Timeout）の場合は専用のメッセージにする
            if (response.status === 504) {
                throw new Error("AWSの通信制限時間（タイムアウト）を超過しました。設定を見直してください。");
            }
            
            const errData = await response.json().catch(() => ({ detail: `サーバーエラーが発生しました (ステータスコード: ${response.status})` }));
            throw new Error(errData.detail || JSON.stringify(errData));
        }
        
        statusDiv.innerText = "✨ パワポファイルの組み立てが完了しました！";
        if (subStatusDiv) subStatusDiv.style.display = 'none'; // 成功したらサブは消す
        
        const result = await response.json();
        window.generatedPptxBase64 = result.pptx_base64;
        window.generatedPamphletFileName = zumen ? `パンフレット_${zumen.name.split('.')[0]}.pptx` : 'パンフレット_自動生成.pptx';
        
        result.preview_images.forEach(item => {
            const card = document.createElement('div');
            card.style = "background: white; border: 1px solid #CFD8DC; border-radius: 6px; padding: 12px; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.05); width: 190px;";
            
            const label = document.createElement('div');
            label.style = "font-weight: bold; font-size: 13px; color: #1E2D3D; margin-bottom: 8px; text-transform: uppercase; border-bottom: 1px solid #E4E7EB; padding-bottom: 4px;";
            label.innerText = item.type;
            
            const img = document.createElement('img');
            img.src = "data:image/jpeg;base64," + item.image;
            img.style = "width: 100%; height: auto; border: 1px solid #E4E7EB; border-radius: 4px;";
            
            card.appendChild(label);
            card.appendChild(img);
            previewContainer.appendChild(card);
        });

        previewSection.classList.remove('hidden');
        alert("🎉 パンフレットの生成が完了しました！下部のプレビューを確認して保存してください。");
        statusDiv.innerText = "";
    } catch (error) {
        isGenerating = false; // ⬅️ ここを新しくします！
        alert("⚠️ 生成中にエラーが発生しました。");
        statusDiv.innerText = "❌ エラーが発生したため処理を中断しました。";
        if (subStatusDiv) subStatusDiv.innerText = "下部のアラートログをご確認ください。";
        
        // 🌟【新設】画面上に生のログを吐き出して見える化する
        if (errorBox && errorText) {
            errorText.innerText = error.message;
            errorBox.classList.remove('hidden');
        }
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
// ==========================================
// 📥 ドラッグ＆ドロップ機能の復活処理（強化版）
// ==========================================
function setupDragAndDrop(inputId) {
    const fileInput = document.getElementById(inputId);
    if (!fileInput) return;
    
    // 親要素、または周囲のアップロードエリアを柔軟に探す
    const dropZone = fileInput.closest('.upload-zone') || fileInput.closest('.file-upload-box') || fileInput.parentNode;
    if (!dropZone) return;

    // マウスがエリアの上に乗った時の処理
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#0056b3';      // 枠線の色を濃い青に変える
        dropZone.style.backgroundColor = '#f0f4f8';  // 背景を少し青っぽくする
    });

    // マウスがエリアから離れた時の処理
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#CFD8DC';      // 元の枠線色に戻す
        dropZone.style.backgroundColor = 'transparent'; // 背景を透明に戻す
    });

    // ファイルがドロップされた時の処理
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#CFD8DC';
        dropZone.style.backgroundColor = 'transparent';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            // ドロップされたファイルをHTMLの入力欄にセットする
            fileInput.files = files;
            
            // ファイル選択された時と同じイベントを強制発生
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    });
}

// 🌟 画面の読み込みがすべて終わった瞬間に、3つの枠にドラッグ＆ドロップを設定する
document.addEventListener("DOMContentLoaded", () => {
    setupDragAndDrop('apb-zumen');  // 販売図面枠
    setupDragAndDrop('apb-madori'); // 間取り図枠
    setupDragAndDrop('apb-empty');  // 空室写真枠
});