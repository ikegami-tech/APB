// ==========================================
// 🌐 1. 全画面共通・初期化処理（会社名自動連動など）
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // 💡 画面が開いた瞬間に、ログイン店舗の会社名に自動で書き換える
    const savedCompanyName = localStorage.getItem("company_name");
    const headerCompany = document.getElementById("header-company-name");
    if (savedCompanyName && headerCompany) {
        headerCompany.innerText = savedCompanyName;
    }

    // 🌟【追加】ログイン店舗に応じてフッターのテキスト（住所・電話番号など）を自動で書き換える
    const savedBranchKey = localStorage.getItem("branch_key");
    const branchInfo = {
        "練馬": {
            license: "東京都知事（4）第86488号",
            address: "〒178-0063 東京都練馬区東大泉1-27-22光和ビル2F",
            tel: "0120-384-700",
            name: "株式会社 東宝ハウス練馬"
        },
        "国分寺": {
            license: "東京都知事（9）第42787号",
            address: "〒185-0021 東京都国分寺市南町3-22-2",
            tel: "0120-13-3107",
            name: "株式会社 東宝ハウス国分寺"
        },
        "武蔵野": {
            license: "東京都知事（3）第90333号",
            address: "〒180-0004 東京都武蔵野市吉祥寺本町1-15-9",
            tel: "0120-15-3101",
            name: "株式会社 東宝ハウス武蔵野"
        }
    };

    if (savedBranchKey && branchInfo[savedBranchKey]) {
        const data = branchInfo[savedBranchKey];
        // 画面上にあるすべてのフッターテキストを一撃で書き換え
        document.querySelectorAll('.foot-license').forEach(el => el.innerText = data.license);
        document.querySelectorAll('.foot-tel').forEach(el => el.innerText = "📞 " + data.tel);
        document.querySelectorAll('.foot-company').forEach(el => el.innerText = data.name);
        document.querySelectorAll('.foot-address').forEach(el => el.innerText = data.address);
    }

// 🌟【追加】ログイン店舗に応じてフッターのロゴ画像を自動で切り替える
    const logoImages = document.querySelectorAll(".footer-logo-img");
    if (savedBranchKey && logoImages.length > 0) {
        let logoSrc = "/static/logo.png"; // デフォルト（国分寺の既存ロゴ）
        
        if (savedBranchKey === "練馬") {
            logoSrc = "/static/logo_nerima.jpg"; // ステップ1で配置した練馬ロゴ
            // 🌟このロゴにCSSを適用するため、クラスを追加する魔法
            logoImages.forEach(img => img.classList.add('footer-logo-img'));
        } else if (savedBranchKey === "武蔵野") {
            logoSrc = "/static/logo_musashino.jpg"; // 武蔵野用（今後用意する場合）
        }
        
        // 画面上にあるすべてのフッターロゴを一撃で書き換え
        logoImages.forEach(img => {
            img.src = logoSrc;
        });
    }

    // APB用のドラッグ＆ドロップのセットアップ（要素が存在する場合のみ安全に実行）
    if (document.getElementById('apb-zumen')) setupDragAndDrop('apb-zumen');
    if (document.getElementById('apb-madori')) setupDragAndDrop('apb-madori');
    if (document.getElementById('apb-empty')) setupDragAndDrop('apb-empty');
// 🌟 すべての画像枠をクリック可能にして裏で繋ぐ魔法（強力版）
    const boxes = document.querySelectorAll('.z-box');
    boxes.forEach(box => {
        // innerHTMLを使うことで、見えない改行やスペースを無視して確実に判定します
        const html = box.innerHTML; 
        let targetId = "";
        let modalTitle = "";
        
        if (html.includes('店舗写真')) { targetId = 'tenpo'; modalTitle = '店舗写真'; }
        else if (html.includes('間取り図')) { targetId = 'madori'; modalTitle = '間取り図'; }
        else if (html.includes('画像1')) { targetId = 'image1'; modalTitle = '画像1'; }
        else if (html.includes('画像2')) { targetId = 'image2'; modalTitle = '画像2'; }
        else if (html.includes('画像3')) { targetId = 'image3'; modalTitle = '画像3'; }
        else if (html.includes('画像4')) { targetId = 'image4'; modalTitle = '画像4'; }
        
        if (targetId) {
            box.setAttribute('data-image-target', targetId);
            // 元々HTMLに書かれているアラート(onclick)を強制的に上書きして無効化します
            box.onclick = function() { window.openImageModal(targetId, modalTitle); };
            box.style.cursor = 'pointer';
        }
    });
}); // 👈 🌟これ（DOMContentLoadedを閉じるカッコ）を1行書き足してください！

// ==========================================
// 🔑 2. ログイン画面用（login.html）の処理
// ==========================================
function handleLogin(event) {
    event.preventDefault(); // 画面の勝手なリロードを防止

    const loginIdInput = document.getElementById('login-id');
    if (!loginIdInput) return;
    const loginId = loginIdInput.value.trim(); 

    let companyName = "株式会社東宝ハウス国分寺"; // 予備のデフォルト
    let branchKey = "国分寺";

    // 入力されたIDに応じて会社名と店舗キーを判定
    if (loginId === "th-nerima") {
        companyName = "株式会社 東宝ハウス練馬";
        branchKey = "練馬";
    } else if (loginId === "musashino") {
        companyName = "株式会社 東宝ハウス武蔵野";
        branchKey = "武蔵野";
    } else if (loginId === "kokubunji" || loginId === "th-kokubunji") {
        companyName = "株式会社 東宝ハウス国分寺";
        branchKey = "国分寺";
    }

    // ブラウザの記憶箱（localStorage）にカチッと保存
    localStorage.setItem("company_name", companyName);
    localStorage.setItem("branch_key", branchKey);

    // 記憶が完了したら、満を持して総合メニュー画面へジャンプ！
    window.location.href = '/menu';
}

// ==========================================
// 📄 3. 販売図面作成画面用（zumen.html）の処理
// ==========================================

// --- 画面遷移の処理 ---
function goToStep2() {
    const propTypeInput = document.getElementById('property-type');
    if (!propTypeInput) return;
    const propType = propTypeInput.value;
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
    const propTypeInput = document.getElementById('property-type');
    if (!propTypeInput) return;
    const propType = propTypeInput.value;
    
    const subtitle = document.getElementById('editor-subtitle');
    if (subtitle) {
        subtitle.innerText = `🎨 編集画面（${propType} / デザイン ${designNum}）`;
    }
    
    document.getElementById('step-2-design').classList.add('hidden');
    document.getElementById('step-3-editor').classList.remove('hidden');

    // 🌟 デザイン1・2・3の表示・hidden切り替え（ガード処理付き）
    const l1 = document.getElementById('zumen-layout-1');
    const l2 = document.getElementById('zumen-layout-2');
    const l3 = document.getElementById('zumen-layout-3');
    
    if(l1) { l1.style.display = 'none'; l1.classList.add('hidden'); }
    if(l2) { l2.style.display = 'none'; l2.classList.add('hidden'); }
    if(l3) { l3.style.display = 'none'; l3.classList.add('hidden'); }
    
    if(designNum === 1 && l1) {
        l1.style.display = 'block';
        l1.classList.remove('hidden');
    } else if(designNum === 2 && l2) {
        l2.style.display = 'flex';
        l2.classList.remove('hidden');
    } else if(designNum === 3 && l3) {
        l3.style.display = 'flex';
        l3.classList.remove('hidden');
    }
}

function goBackToStep2() {
    document.getElementById('step-3-editor').classList.add('hidden');
    document.getElementById('step-2-design').classList.remove('hidden');
}

// --- モーダルと通信処理 ---
function openModal(id) { 
    document.getElementById(id).style.display = 'block';
}
function closeModal(id) { 
    document.getElementById(id).style.display = 'none'; 
}

async function sendDataToPython(formData) {
    try {
        const response = await fetch("/generate_zumen", { method: "POST", body: formData });
        const result = await response.json();
        console.log("Pythonからの返事:", result.message);
    } catch (error) { console.error("通信エラー", error); }
}
// 🌟 全デザインの文字を同時に書き換える連動装置（空欄非表示対応版）
window.syncDisplays = function() {
    try {
        const items = [
            'display-title', 'display-price', 'display-line', 'display-station', 'display-walk',
            'display-address', 'display-land-right', 'display-exclusive-area', 'display-balcony-area',
            'display-floor', 'display-total-units', 'display-structure', 'display-build-date',
            'display-layout', 'display-water', 'display-sewage', 'display-gas', 'display-status',
            'display-delivery', 'display-parking', 'display-bike', 'display-bicycle',
            'display-developer', 'display-builder', 'display-management', 'display-zoning',
            'display-admin-fee', 'display-repair-fund', 'display-other-fee', 'display-pet', 'display-elevator'
        ];
        items.forEach(function(item) {
            const baseEl = document.getElementById(item);
            if (baseEl) {
                const val = baseEl.innerText;
                const d2El = document.getElementById(item + '-d2');
                const d3El = document.getElementById(item + '-d3');

                const toggleVisibility = (el, value) => {
                    if (el) {
                        el.innerText = value;
                        // もし親要素が物件概要のリスト（■が含まれる）なら、空の時は消す
                        if (el.parentNode && el.parentNode.innerText.includes('■')) {
                            el.parentNode.style.display = value.trim() === '' ? 'none' : '';
                        }
                    }
                };

                toggleVisibility(d2El, val);
                toggleVisibility(d3El, val);
            }
        });
    } catch (e) { console.error('syncDisplays Error:', e); }
};

// 🌟 物件概要の保存処理（空欄非表示対応版）
window.saveSummary = function() {
    const summaryItems = [
        'address', 'land-right', 'exclusive-area', 'balcony-area',
        'floor', 'total-units', 'structure', 'build-date',
        'layout', 'water', 'sewage', 'gas', 'status',
        'delivery', 'parking', 'bike', 'bicycle',
        'developer', 'builder', 'management', 'zoning',
        'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator'
    ];
    summaryItems.forEach(function(item) {
        const dispEl = document.getElementById('display-' + item);
        const inpEl = document.getElementById('input-' + item);
        if (dispEl && inpEl) {
            const val = inpEl.value.trim();
            dispEl.innerText = val;
            
            // 💡 ここが魔法！入力が空なら、その行（div）ごと非表示にする！
            if (dispEl.parentNode) {
                dispEl.parentNode.style.display = val === '' ? 'none' : '';
            }
        }
    });
    closeModal('summaryModal');
    setTimeout(window.syncDisplays, 50);
};

// 🌟 交通アクセスの保存処理
function saveAccess() {
    document.getElementById('display-line').innerText = document.getElementById('input-line').value;
    document.getElementById('display-station').innerText = document.getElementById('input-station').value;
    document.getElementById('display-walk').innerText = document.getElementById('input-walk').value;
    closeModal('accessModal');
    setTimeout(window.syncDisplays, 50);
}

// 🌟 タイトルの保存処理
function saveTitle() {
    const newTitle = document.getElementById('input-title').value;
    document.getElementById('display-title').innerText = newTitle;
    closeModal('titleModal');
    setTimeout(window.syncDisplays, 50);
}

// 🌟 販売価格の保存処理
function saveInfo() {
    document.getElementById('display-price').innerText = document.getElementById('input-price').value;
    closeModal('infoModal');
    setTimeout(window.syncDisplays, 50);
}

// 🌟 画像モーダルを開く処理
window.currentImageTargetId = null;
window.openImageModal = function(targetId, title) {
    window.currentImageTargetId = targetId;
    const titleEl = document.querySelector('#imageModal h3');
    if (titleEl) titleEl.innerText = `🖼️ ${title}のアップロード`;
    const fileInput = document.getElementById('input-image');
    if (fileInput) fileInput.value = '';
    
    const textWrapper = document.getElementById('modal-text-input-wrapper');
    const textInput = document.getElementById('modal-image-text');
    if (textWrapper && textInput) {
        if (targetId === 'tenpo') {
            textWrapper.style.display = 'block';
            const currentTextEl = document.getElementById('tenpo-text');
            textInput.value = currentTextEl ? currentTextEl.innerText : '「住まい」のもっと先へ。';
        } else {
            textWrapper.style.display = 'none';
            textInput.value = '';
        }
    }
    openModal('imageModal');
};

// 🌟 画像の保存処理
window.saveImage = function() {
    const fileInput = document.getElementById('input-image');
    if (!fileInput) return;
    const file = fileInput.files[0];
    if (file && window.currentImageTargetId) {
        const imageUrl = URL.createObjectURL(file);
        const targets = document.querySelectorAll(`[data-image-target="${window.currentImageTargetId}"]`);
        targets.forEach(target => {
            target.style.backgroundImage = `url(${imageUrl})`;
            target.style.backgroundSize = 'cover';
            target.style.backgroundPosition = 'center';
            target.style.backgroundRepeat = 'no-repeat';
            target.style.color = 'transparent';
        });
        if (!window.uploadedImages) window.uploadedImages = {};
        window.uploadedImages[window.currentImageTargetId] = file;
    }
    if (window.currentImageTargetId === 'tenpo') {
        const textInput = document.getElementById('modal-image-text');
        const currentTextEl = document.getElementById('tenpo-text');
        if (textInput && currentTextEl && textInput.value.trim() !== '') {
            currentTextEl.innerText = textInput.value.trim();
        }
    }
    closeModal('imageModal');
};

async function downloadPptx() {
    const btn = document.querySelector('button[onclick="downloadPptx()"]');
    if (!btn) return;
    const originalText = btn.innerText;
    btn.innerText = "⏳ パワポを作成中...";
    btn.disabled = true;
    try {
        const formData = new FormData();
        // 画面のテキストをすべて収集してPythonに送る
        formData.append("title", document.getElementById('display-title').innerText);
        formData.append("price", document.getElementById('display-price').innerText);
        formData.append("address", document.getElementById('display-address').innerText);
        formData.append("transport_station", document.getElementById('display-station').innerText);
        formData.append("transport_walk", document.getElementById('display-walk').innerText);
        formData.append("madori", document.getElementById('display-layout').innerText);
        formData.append("age", document.getElementById('display-build-date').innerText);
        formData.append("right", document.getElementById('display-land-right').innerText);
        formData.append("land_area", document.getElementById('display-exclusive-area').innerText);
        formData.append("building_area", document.getElementById('display-balcony-area').innerText);
        formData.append("plan", document.getElementById('display-zoning').innerText);

        // 🌟 一番重要：ログイン中の店舗名を裏側に送る
        const branchKey = localStorage.getItem("branch_key") || "国分寺";
        formData.append("branch_name", branchKey);

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
// 🏡 4. APB（パンフレット自動作成）用の処理
// ==========================================
async function startApbGeneration() {
    const btn = document.querySelector('.btn-apb-generate') || document.querySelector('button[onclick="startApbGeneration()"]');
    const statusDiv = document.getElementById('progress-status');
    const subStatusDiv = document.getElementById('progress-sub-status');
    const errorBox = document.getElementById('error-log-box');
    const errorText = document.getElementById('error-log-text');
    const previewSection = document.getElementById('apb-preview-section');
    const previewContainer = document.getElementById('apb-preview-images');
    if (!btn || !statusDiv) return;
    const originalText = btn.innerText;

    // 前回の表示をすべてリセット
    if (previewSection) previewSection.classList.add('hidden');
    if (previewContainer) previewContainer.innerHTML = "";
    if (errorBox) errorBox.classList.add('hidden');
    
    // 🌟 生成ボタンが押された瞬間に「※AIが稼働中です」を表示させる連動
    if (subStatusDiv) subStatusDiv.style.display = 'block'; 

    window.generatedPptxBase64 = null;
    btn.innerText = "⏳ パンフレットを作成中...";
    btn.disabled = true;
    statusDiv.innerText = "🚀 処理を開始しています...";

    const formData = new FormData();
    const zumen = document.getElementById('apb-zumen')?.files[0];
    const madori = document.getElementById('apb-madori')?.files[0];
    const empty = document.getElementById('apb-empty')?.files[0];
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

    let isPolling = true;
    const progressTimer = setInterval(async () => {
        if (!isPolling) return;
        try {
            const res = await fetch("/apb_progress");
            if (res.ok) {
                const data = await res.json();
                if (isPolling) {
                    statusDiv.innerText = data.message;
                    if (subStatusDiv) subStatusDiv.style.display = 'none';
                }
            }
        } catch (e) {}
    }, 2000);

    try {
        const response = await fetch("/generate_apb", { method: "POST", body: formData });
        isPolling = false;
        clearInterval(progressTimer);
        
        if (!response.ok) {
            if (response.status === 504) {
                throw new Error("AWSの通信制限時間（タイムアウト）を超過しました。設定を見直してください。");
            }
            const errData = await response.json().catch(() => ({ detail: `サーバーエラーが発生しました (ステータスコード: ${response.status})` }));
            throw new Error(errData.detail || JSON.stringify(errData));
        }
        
        statusDiv.innerText = "✨ パワポファイルの組み立てが完了しました！";
        if (subStatusDiv) subStatusDiv.style.display = 'none';
        
        const result = await response.json();
        window.generatedPptxBase64 = result.pptx_base64;
        window.generatedPamphletFileName = zumen ? `パンフレット_${zumen.name.split('.')[0]}.pptx` : 'パンフレット_自動生成.pptx';
        
        if (previewContainer) {
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
        }
        if (previewSection) previewSection.classList.remove('hidden');
        alert("🎉 パンフレットの生成が完了しました！下部のプレビューを確認して保存してください。");
        statusDiv.innerText = "";
    } catch (error) {
        clearInterval(progressTimer);
        alert("⚠️ 生成中にエラーが発生しました。");
        statusDiv.innerText = "❌ エラーが発生したため処理を中断しました。";
        if (subStatusDiv) subStatusDiv.innerText = "下部のアラートログをご確認ください。";
        
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

function downloadGeneratedPamphlet() {
    if (!window.generatedPptxBase64) {
        alert("⚠️ 保存するデータが見つかりません。もう一度生成し直してください。");
        return;
    }
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

// --- ドラッグ＆ドロップ機能 ---
function setupDragAndDrop(inputId) {
    const fileInput = document.getElementById(inputId);
    if (!fileInput) return;
    
    const dropZone = fileInput.closest('.upload-zone') || fileInput.closest('.file-upload-box') || fileInput.parentNode;
    if (!dropZone) return;
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#0056b3';
        dropZone.style.backgroundColor = '#f0f4f8';
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = '#CFD8DC';
        dropZone.style.backgroundColor = 'transparent';
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '#CFD8DC';
        dropZone.style.backgroundColor = 'transparent';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        }
    });
}
// 🌟 ページを開いた瞬間に、最初から空の項目を隠して綺麗に並べる処理
document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        const summaryItems = [
            'address', 'land-right', 'exclusive-area', 'balcony-area',
            'floor', 'total-units', 'structure', 'build-date',
            'layout', 'water', 'sewage', 'gas', 'status',
            'delivery', 'parking', 'bike', 'bicycle',
            'developer', 'builder', 'management', 'zoning',
            'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator'
        ];
        summaryItems.forEach(function(item) {
            const dispEl = document.getElementById('display-' + item);
            const inpEl = document.getElementById('input-' + item);
            if (dispEl && inpEl) {
                dispEl.innerText = inpEl.value.trim();
                if (dispEl.parentNode) {
                    dispEl.parentNode.style.display = inpEl.value.trim() === '' ? 'none' : '';
                }
            }
        });
        if (typeof window.syncDisplays === 'function') window.syncDisplays();
    }, 100);
});