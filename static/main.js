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
            logoSrc = "/static/logo_nerima.png"; // ステップ1で配置した練馬ロゴ
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

    // 🌟【追加】初期表示時に、中身が空の物件詳細情報（■〇〇 / ）をすべて非表示にする
    const summaryItemNames = [
        'address', 'land-right', 'exclusive-area', 'balcony-area',
        'floor', 'total-units', 'structure', 'build-date',
        'layout', 'water', 'sewage', 'gas', 'status',
        'delivery', 'parking', 'bike', 'bicycle',
        'developer', 'builder', 'management', 'zoning',
        'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator',
        'land-area', 'building-area', 'city-planning', 'road', 'coverage', 'floor-ratio'
    ];
    
    // 全デザイン（1, 2, 3）に対して一気に処理を行う
    ['', '-d2', '-d3'].forEach(suffix => {
        summaryItemNames.forEach(item => {
            const el = document.getElementById('display-' + item + suffix);
            // 項目が存在し、かつ親要素（行）に「■」が含まれているか確認
            if (el && el.parentNode && el.parentNode.innerText.includes('■')) {
                // 中身（値）が空っぽなら、親要素（項目名が書かれている行）ごと隠す！
                if (el.innerText.trim() === '') {
                    el.parentNode.style.display = 'none';
                }
            }
        });
    });

});

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

function goToStep2() {
    const propTypeInput = document.getElementById('property-type');
    if (!propTypeInput) return;
    const propType = propTypeInput.value;
    if (!propType) {
        alert('🚨 物件種別（マンションか戸建て）を選択してください！');
        return;
    }

// 🌟 追加：マンションと戸建てで項目を自動で切り替える魔法（空欄非表示対応版）
    const isMansion = (propType === "マンション");

    document.querySelectorAll('.only-mansion').forEach(el => {
        if (!isMansion) {
            el.style.display = 'none';
        } else {
            const span = el.querySelector('span');
            // プレビュー枠(spanがある)かつ空欄なら隠す。入力枠(spanがない)は表示。
            el.style.display = (span && span.innerText.trim() === '') ? 'none' : '';
        }
    });

    document.querySelectorAll('.only-kodate').forEach(el => {
        if (isMansion) {
            el.style.display = 'none';
        } else {
            const span = el.querySelector('span');
            el.style.display = (span && span.innerText.trim() === '') ? 'none' : '';
        }
    });

    // 👇この2行は画面を切り替えるための大事な処理なので残します！
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
// 🌟 モーダルを開くときに、現在のデザインのテキストを入力欄にセットし直す魔法
function openModal(id) {
    const suffix = getCurrentDesignSuffix(); // 現在のデザインを判定
    
    // 物件概要モーダルの場合
    if (id === 'summaryModal') {
        const summaryItems = [
            'address', 'land-right', 'exclusive-area', 'balcony-area',
            'floor', 'total-units', 'structure', 'build-date',
            'layout', 'water', 'sewage', 'gas', 'status',
            'delivery', 'parking', 'bike', 'bicycle',
            'developer', 'builder', 'management', 'zoning',
            'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator',
            'land-area', 'building-area', 'city-planning', 'road', 'coverage', 'floor-ratio'
        ];
        summaryItems.forEach(item => {
            const dispEl = document.getElementById('display-' + item + suffix);
            const inpEl = document.getElementById('input-' + item);
            if (dispEl && inpEl) {
                inpEl.value = dispEl.innerText;
            }
        });
    } 
    // タイトルモーダルの場合
    else if (id === 'titleModal') {
        const dispEl = document.getElementById('display-title' + suffix);
        const inpEl = document.getElementById('input-title');
        if (dispEl && inpEl) {
            inpEl.value = (dispEl.innerText !== 'タイトル' && dispEl.innerText !== 'タイトルを入力') ? dispEl.innerText : '';
        }
    } 
    // 販売価格モーダルの場合
    else if (id === 'infoModal') {
        const dispEl = document.getElementById('display-price' + suffix);
        const inpEl = document.getElementById('input-price');
        if (dispEl && inpEl) inpEl.value = dispEl.innerText;
    } 
// 交通アクセスモーダルの場合
    else if (id === 'accessModal') {
        const lineDisp = document.getElementById('display-line' + suffix);
        const lineInp = document.getElementById('input-line');
        if (lineDisp && lineInp) {
            lineInp.value = lineDisp.innerText !== '交通' ? lineDisp.innerText : '';
            // 🌟 路線がセットされたら、裏で駅リストのプルダウンを自動生成する
            if (typeof window.updateStations === 'function') window.updateStations();
        }
        
        const stationDisp = document.getElementById('display-station' + suffix);
        const stationInp = document.getElementById('input-station');
        if (stationDisp && stationInp) {
            const cleanText = stationDisp.innerText.replace(/[「」]/g, '');
            stationInp.value = cleanText !== '最寄駅' ? cleanText : '';
        }
        
        const walkDisp = document.getElementById('display-walk' + suffix);
        const walkInp = document.getElementById('input-walk');
        if (walkDisp && walkInp) walkInp.value = walkDisp.innerText !== '〇' ? walkDisp.innerText : '';
    }

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
// 🌟 デザイン2の案内テキストと項目の表示切り替え魔法（全項目チェック版）
        const hintD2 = document.getElementById('display-empty-hint-d2');
        const containerD2 = document.getElementById('display-summary-container-d2');
        
        if (hintD2 && containerD2) {
            const summaryItems = [
                'address', 'land-right', 'exclusive-area', 'balcony-area',
                'floor', 'total-units', 'structure', 'build-date',
                'layout', 'water', 'sewage', 'gas', 'status',
                'delivery', 'parking', 'bike', 'bicycle',
                'developer', 'builder', 'management', 'zoning',
                'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator'
            ];
            
            // 26個の項目のうち、1つでも中身が入っているか確認する
            let hasInput = false;
            summaryItems.forEach(item => {
                const el = document.getElementById('display-' + item + '-d2');
                if (el) {
                    const txt = el.innerText.trim();
                    if (txt !== "" && txt !== "東京都国分寺市...") {
                        hasInput = true;
                    }
                }
            });
            
// 🌟 どれか1つでも入力があれば項目を表示（見出しは消さない！）
            if (hasInput) {
                containerD2.classList.remove('hidden');
            } else {
                containerD2.classList.add('hidden');
            }
        }

        // 🌟 追加：デザイン3の案内テキストと項目の表示切り替え魔法
        const hintD3 = document.getElementById('display-empty-hint-d3');
        const containerD3 = document.getElementById('display-summary-container-d3');
        
        if (hintD3 && containerD3) {
            let hasInputD3 = false;
            const summaryItemsD3 = [
                'address', 'land-right', 'exclusive-area', 'balcony-area',
                'floor', 'total-units', 'structure', 'build-date',
                'layout', 'water', 'sewage', 'gas', 'status',
                'delivery', 'parking', 'bike', 'bicycle',
                'developer', 'builder', 'management', 'zoning',
                'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator'
            ];
            
            summaryItemsD3.forEach(item => {
                const el = document.getElementById('display-' + item + '-d3');
                if (el) {
                    const txt = el.innerText.trim();
                    if (txt !== "" && txt !== "東京都国分寺市...") {
                        hasInputD3 = true;
                    }
                }
            });
            
            // どれか1つでも入力があれば、案内ラベルを隠してリストを表示
            if (hasInputD3) {
                hintD3.style.display = 'none';
                containerD3.classList.remove('hidden');
            } else {
                hintD3.style.display = 'block';
                containerD3.classList.add('hidden');
            }
        }
};

// 🌟 物件概要の保存処理（独立・表示切替対応版に修正）
window.saveSummary = function() {
    const summaryItems = [
        'address', 'land-right', 'exclusive-area', 'balcony-area',
        'floor', 'total-units', 'structure', 'build-date',
        'layout', 'water', 'sewage', 'gas', 'status',
        'delivery', 'parking', 'bike', 'bicycle',
        'developer', 'builder', 'management', 'zoning',
        'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator',
        'land-area', 'building-area', 'city-planning', 'road', 'coverage', 'floor-ratio'
    ];
    
    const suffix = getCurrentDesignSuffix(); // 現在のデザインを判定
    let hasInput = false; // 入力があるかどうかのフラグ
    
    summaryItems.forEach(function(item) {
        const dispEl = document.getElementById('display-' + item + suffix);
        const inpEl = document.getElementById('input-' + item);
        if (dispEl && inpEl) {
            const val = inpEl.value.trim();
            dispEl.innerText = val;
            
            if (val !== "") {
                hasInput = true; // 1つでも入力があればフラグを立てる
            }
            
            // 行ごとの表示・非表示（空欄なら詰める処理）
            if (dispEl.parentNode) {
                dispEl.parentNode.style.display = val === '' ? 'none' : '';
            }
        }
    });
    
    // 🌟 デザイン2のコンテナ表示切り替え
    if (suffix === '-d2') {
        const containerD2 = document.getElementById('display-summary-container-d2');
        if (containerD2) {
            if (hasInput) {
                containerD2.classList.remove('hidden'); // 入力があれば表示！
            } else {
                containerD2.classList.add('hidden');
            }
        }
    }
    // 🌟 デザイン3のコンテナ表示切り替え
    else if (suffix === '-d3') {
        const hintD3 = document.getElementById('display-empty-hint-d3');
        const containerD3 = document.getElementById('display-summary-container-d3');
        if (containerD3) {
            if (hasInput) {
                if (hintD3) hintD3.style.display = 'none';
                containerD3.classList.remove('hidden'); // 入力があれば表示！
            } else {
                if (hintD3) hintD3.style.display = 'block';
                containerD3.classList.add('hidden');
            }
        }
    }

    closeModal('summaryModal');
};

// 🌟 交通アクセスの保存処理（独立版に修正）
function saveAccess() {
    const suffix = getCurrentDesignSuffix();
    const lineEl = document.getElementById('display-line' + suffix);
    const stationEl = document.getElementById('display-station' + suffix);
    const walkEl = document.getElementById('display-walk' + suffix);
    
    if (lineEl) lineEl.innerText = document.getElementById('input-line').value;
    if (stationEl) stationEl.innerText = document.getElementById('input-station').value;
    if (walkEl) walkEl.innerText = document.getElementById('input-walk').value;
    
    closeModal('accessModal');
}
// 🌟 現在表示中のデザイン番号を取得する魔法（新規追加）
function getCurrentDesignSuffix() {
    if (document.getElementById('zumen-layout-2') && !document.getElementById('zumen-layout-2').classList.contains('hidden')) {
        return '-d2';
    } else if (document.getElementById('zumen-layout-3') && !document.getElementById('zumen-layout-3').classList.contains('hidden')) {
        return '-d3';
    }
    return ''; // デザイン1の場合はサフィックス（接尾辞）なし
}
// 🌟 タイトルの保存処理（独立版に修正）
function saveTitle() {
    const newTitle = document.getElementById('input-title').value;
    const suffix = getCurrentDesignSuffix(); // 現在のデザインを判定
    const displayEl = document.getElementById('display-title' + suffix);
    if (displayEl) displayEl.innerText = newTitle;
    
    closeModal('titleModal');
    // setTimeout(window.syncDisplays, 50); ← これを消すことで連動をストップ
}
// 🌟 販売価格の保存処理（独立版に修正）
function saveInfo() {
    const newPrice = document.getElementById('input-price').value;
    const suffix = getCurrentDesignSuffix();
    const displayEl = document.getElementById('display-price' + suffix);
    if (displayEl) displayEl.innerText = newPrice;
    
    closeModal('infoModal');
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

// 🌟 画像の保存処理（即時反映・自動クローズ版に修正）
window.saveImage = function() {
    const fileInput = document.getElementById('input-image');
    if (!fileInput) return;
    const file = fileInput.files[0];
    if (file && window.currentImageTargetId) {
        const imageUrl = URL.createObjectURL(file);
        // 今表示しているデザインレイアウトのIDを特定する
        let currentLayoutId = 'zumen-layout-1';
        if (document.getElementById('zumen-layout-2') && !document.getElementById('zumen-layout-2').classList.contains('hidden')) {
            currentLayoutId = 'zumen-layout-2';
        } else if (document.getElementById('zumen-layout-3') && !document.getElementById('zumen-layout-3').classList.contains('hidden')) {
            currentLayoutId = 'zumen-layout-3';
        }
        
        // 現在のデザインの中にある画像枠だけを狙い撃ちで書き換える
        const parentEl = document.getElementById(currentLayoutId);
        if (parentEl) {
            const targets = parentEl.querySelectorAll(`[data-image-target="${window.currentImageTargetId}"]`);
            targets.forEach(target => {
                target.style.backgroundImage = `url(${imageUrl})`;
                target.style.backgroundPosition = 'center';
                target.style.backgroundRepeat = 'no-repeat';
                target.style.color = 'transparent'; // 文字を消す
                
                if (window.currentImageTargetId.startsWith('icon')) {
                    target.style.backgroundSize = 'contain';
                    target.style.setProperty('background-color', 'transparent', 'important');
                    target.style.border = 'none';
                    target.style.boxShadow = 'none';
                    target.style.padding = '0';
                } else {
                    target.style.backgroundSize = 'cover';
                }
            });
        }
        
        // パワポ送信用の記憶
        if (!window.uploadedImages) window.uploadedImages = {};
        window.uploadedImages[window.currentImageTargetId] = file;
    }
    
    // 店舗テキスト処理（デザイン1用）
    if (window.currentImageTargetId === 'tenpo') {
        const textInput = document.getElementById('modal-image-text');
        const currentTextEl = document.getElementById('tenpo-text');
        if (textInput && currentTextEl && textInput.value.trim() !== '') {
            currentTextEl.innerText = textInput.value.trim();
        }
    }
    
    // 🌟 処理が終わったら、ファイル選択欄をリセットしてモーダルを自動で閉じる
    fileInput.value = '';
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

        // 🌟【最重要】今どのデザインを表示しているかを判定してPythonに伝える魔法
        let currentDesign = "1"; // デフォルト
        if (document.getElementById('zumen-layout-2') && !document.getElementById('zumen-layout-2').classList.contains('hidden')) {
            currentDesign = "2";
        } else if (document.getElementById('zumen-layout-3') && !document.getElementById('zumen-layout-3').classList.contains('hidden')) {
            currentDesign = "3";
        }
        formData.append("design_num", currentDesign);

        // 各デザインの画面から現在表示されているテキストを正しく収集する処理
        let suffix = currentDesign === "1" ? "" : "-d" + currentDesign;
        
        const titleText = document.getElementById('display-title' + (currentDesign === "1" ? "" : suffix))?.innerText || "";
        const priceText = document.getElementById('display-price' + suffix)?.innerText || "";
        const addressText = document.getElementById('display-address' + suffix)?.innerText || "";
        const stationText = document.getElementById('display-station' + suffix)?.innerText || "";
        const walkText = document.getElementById('display-walk' + suffix)?.innerText || "";
        const layoutText = document.getElementById('display-layout' + suffix)?.innerText || "";
        const buildDateText = document.getElementById('display-build-date' + suffix)?.innerText || "";
        const landRightText = document.getElementById('display-land-right' + suffix)?.innerText || "";
        const exclusiveAreaText = document.getElementById('display-exclusive-area' + suffix)?.innerText || "";
        const balconyAreaText = document.getElementById('display-balcony-area' + suffix)?.innerText || "";
        const zoningText = document.getElementById('display-zoning' + suffix)?.innerText || "";

        formData.append("title", titleText);
        formData.append("price", priceText);
        formData.append("address", addressText);
        formData.append("transport_station", stationText);
        formData.append("transport_walk", walkText);
        formData.append("madori", layoutText);
        formData.append("age", buildDateText);
        formData.append("right", landRightText);
        formData.append("land_area", exclusiveAreaText);
        formData.append("building_area", balconyAreaText);
        formData.append("plan", zoningText);

        // 🌟【新規追加】物件概要の全項目を画面から直接収集してひとまとめにする魔法
        let fullSummaryParts = [];
        const summaryItemNames = [
            'address', 'land-right', 'exclusive-area', 'balcony-area',
            'floor', 'total-units', 'structure', 'build-date',
            'layout', 'water', 'sewage', 'gas', 'status',
            'delivery', 'parking', 'bike', 'bicycle',
            'developer', 'builder', 'management', 'zoning',
            'admin-fee', 'repair-fund', 'other-fee', 'pet', 'elevator',
            'land-area', 'building-area', 'city-planning', 'road', 'coverage', 'floor-ratio'
        ];
        
        summaryItemNames.forEach(item => {
            const el = document.getElementById('display-' + item + suffix);
            // 要素が存在し、中身が空でなく、親要素（行）が表示されている場合のみ取得
            if (el && el.innerText.trim() !== '' && el.parentNode && el.parentNode.style.display !== 'none') {
                const text = el.parentNode.innerText.replace(/\r?\n/g, '').trim();
                fullSummaryParts.push(text);
            }
        });
        // 全項目を「|||」という特殊な文字で区切ってPythonに送信！
        formData.append("full_summary", fullSummaryParts.join('|||'));

// 🌟 ログイン中の店舗名を裏側に送る
        const branchKey = localStorage.getItem("branch_key") || "国分寺";
        formData.append("branch_name", branchKey);

        // 各種画像データ（画像1〜4、間取り、店舗写真）の送信
        if (window.uploadedImages) {
            if (window.uploadedImages['image1']) formData.append("main_image", window.uploadedImages['image1']);
            if (window.uploadedImages['image2']) formData.append("sub_image1", window.uploadedImages['image2']);
            if (window.uploadedImages['image3']) formData.append("sub_image2", window.uploadedImages['image3']);
            if (window.uploadedImages['image4']) formData.append("sub_image3", window.uploadedImages['image4']);
            if (window.uploadedImages['madori']) formData.append("madori_image", window.uploadedImages['madori']);
            if (window.uploadedImages['tenpo']) formData.append("tenpo_image", window.uploadedImages['tenpo']);
            
            // 🌟 追加：設備アイコン画像（1〜6）の送信
            for (let i = 1; i <= 6; i++) {
                if (window.uploadedImages[`icon${i}`]) {
                    formData.append(`icon_image${i}`, window.uploadedImages[`icon${i}`]);
                }
            }
        }

        const response = await fetch("/generate_zumen_file", { method: "POST", body: formData });
        if (!response.ok) throw new Error("サーバーエラー");
        
        const blob = await response.blob();
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = `販売図面_デザイン${currentDesign}_${titleText}.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(a.href);
    } catch (error) {
        console.error(error);
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
// 🌟【APB新規機能】図面がアップロードされた瞬間に裏で住所を自動解析する魔法
document.addEventListener("DOMContentLoaded", () => {
    const apbZumenInput = document.getElementById('apb-zumen'); // HTMLのinputのIDに合わせてください
    
    if (apbZumenInput) {
        apbZumenInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // 地図表示エリアを表示し、「解析中」にする
            const mapSection = document.getElementById('apb-auto-map-section');
            const addressText = document.getElementById('apb-extracted-address-text');
            const mapIframe = document.getElementById('apb-google-map-iframe');
            
            if (mapSection) mapSection.classList.remove('hidden');
            if (addressText) addressText.innerText = "⏳ AIが販売図面から住所を読み取っています...";
            if (mapIframe) mapIframe.src = ""; // 一旦クリア
            
            // FormDataを作って、選択されたファイルを裏でPythonへ送信！
            const formData = new FormData();
            formData.append("zumen_file", file);
            
            try {
                const response = await fetch("/apb/extract_address", {
                    method: "POST",
                    body: formData
                });
                const result = await response.json();
                
                if (result.status === "success" && result.address) {
                    // 1. 読み取った住所を画面に表示
                    addressText.innerText = result.address;
                    
                    // 2. GoogleマップのURLを組み立ててiframeを起動！
                    const mapUrl = `https://www.google.com/maps?q=${encodeURIComponent(result.address)}&output=embed`;
                    mapIframe.src = mapUrl;
                } else {
                    addressText.innerText = "❌ 住所の自動抽出に失敗しました。手動で入力してください。";
                }
            } catch (error) {
                console.error("住所解析通信エラー:", error);
                addressText.innerText = "❌ 通信エラーが発生しました。";
            }
        });
    }
});
// ==========================================
// 🚆 5. 関東主要路線のデータとプルダウン連動処理
// ==========================================
// 名前（あいうえお）順、下りの始発駅からの順番で登録しています
const kantoTrainData = [
    { line: "JR京浜東北線", stations: ["大宮", "さいたま新都心", "与野", "北浦和", "浦和", "南浦和", "蕨", "西川口", "川口", "赤羽", "東十条", "王子", "上野", "御徒町", "秋葉原", "神田", "東京", "有楽町", "新橋", "浜松町", "田町", "高輪ゲートウェイ", "品川", "大井町", "大森", "蒲田", "川崎", "鶴見", "新子安", "東神奈川", "横浜"] },
    { line: "JR埼京線", stations: ["大崎", "恵比寿", "渋谷", "新宿", "池袋", "板橋", "十条", "赤羽", "北赤羽", "浮間舟渡", "戸田公園", "戸田", "北戸田", "武蔵浦和", "中浦和", "南与野", "与野本町", "北与野", "大宮"] },
    { line: "JR中央線", stations: ["東京", "神田", "御茶ノ水", "水道橋", "飯田橋", "市ケ谷", "四ツ谷", "信濃町", "千駄ケ谷", "代々木", "新宿", "大久保", "東中野", "中野", "高円寺", "阿佐ケ谷", "荻窪", "西荻窪", "吉祥寺", "三鷹", "武蔵境", "東小金井", "武蔵小金井", "国分寺", "西国分寺", "国立", "立川", "日野", "豊田", "八王子", "西八王子", "高尾"] },
    { line: "JR山手線", stations: ["品川", "大崎", "五反田", "目黒", "恵比寿", "渋谷", "原宿", "代々木", "新宿", "新大久保", "高田馬場", "目白", "池袋", "大塚", "巣鴨", "駒込", "田端", "西日暮里", "日暮里", "鶯谷", "上野", "御徒町", "秋葉原", "神田", "東京", "有楽町", "新橋", "浜松町", "田町", "高輪ゲートウェイ"] },
    { line: "京王線", stations: ["新宿", "笹塚", "代田橋", "明大前", "下高井戸", "桜上水", "上北沢", "八幡山", "芦花公園", "千歳烏山", "仙川", "つつじヶ丘", "柴崎", "国領", "布田", "調布", "西調布", "飛田給", "武蔵野台", "多磨霊園", "白糸台", "東府中", "府中", "分倍河原", "中河原", "聖蹟桜ヶ丘", "百草園", "高幡不動", "南平", "平山城址公園", "長沼", "北野", "京王八王子"] },
    { line: "京王井の頭線", stations: ["渋谷", "神泉", "駒場東大前", "池ノ上", "下北沢", "新代田", "明大前", "永福町", "西永福", "浜田山", "高井戸", "富士見ヶ丘", "久我山", "三鷹台", "井の頭公園", "吉祥寺"] },
    { line: "小田急小田原線", stations: ["新宿", "南新宿", "参宮橋", "代々木八幡", "代々木上原", "東北沢", "下北沢", "世田谷代田", "梅ヶ丘", "豪徳寺", "経堂", "千歳船橋", "祖師ヶ谷大蔵", "成城学園前", "喜多見", "狛江", "和泉多摩川", "登戸", "向ヶ丘遊園", "生田", "読売ランド前", "百合ヶ丘", "新百合ヶ丘", "柿生", "鶴川", "玉川学園前", "町田", "相模大野"] },
    { line: "西武新宿線", stations: ["西武新宿", "高田馬場", "下落合", "中井", "新井薬師前", "沼袋", "野方", "都立家政", "鷺ノ宮", "下井草", "井荻", "上井草", "上石神井", "武蔵関", "東伏見", "西武柳沢", "田無", "花小金井", "小平", "久米川", "東村山", "所沢", "航空公園", "新所沢", "入曽", "狭山市", "新狭山", "南大塚", "本川越"] },
    { line: "西武池袋線", stations: ["池袋", "椎名町", "東長崎", "江古田", "桜台", "練馬", "中村橋", "富士見台", "練馬高野台", "石神井公園", "大泉学園", "保谷", "ひばりヶ丘", "東久留米", "清瀬", "秋津", "所沢", "西所沢", "小手指", "狭山ヶ丘", "武蔵藤沢", "稲荷山公園", "入間市", "仏子", "元加治", "飯能"] },
    { line: "東武東上線", stations: ["池袋", "北池袋", "下板橋", "大山", "中板橋", "ときわ台", "上板橋", "東武練馬", "下赤塚", "成増", "和光市", "朝霞", "朝霞台", "志木", "柳瀬川", "みずほ台", "鶴瀬", "ふじみ野", "上福岡", "新河岸", "川越", "川越市", "霞ヶ関"] }
    // 💡 さらに路線を増やしたい場合は、ここに同じ形式で追加してください！
];

window.updateStations = function() {
    const lineInp = document.getElementById('input-line');
    const stationInp = document.getElementById('input-station');
    if (!lineInp || !stationInp) return;
    
    // 現在の駅の選択をクリア
    stationInp.innerHTML = '<option value="">駅を選択してください</option>';
    
    const selectedLine = lineInp.value;
    const lineData = kantoTrainData.find(d => d.line === selectedLine);
    
    if (lineData) {
        lineData.stations.forEach(station => {
            const opt = document.createElement('option');
            opt.value = station;
            opt.innerText = station;
            stationInp.appendChild(opt);
        });
    } else {
        stationInp.innerHTML = '<option value="">先に路線を選択してください</option>';
    }
};

// ページ読み込み時に「路線」のプルダウンを自動構築する
document.addEventListener("DOMContentLoaded", () => {
    const lineInp = document.getElementById('input-line');
    if (lineInp) {
        lineInp.innerHTML = '<option value="">路線を選択してください</option>';
        kantoTrainData.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.line;
            opt.innerText = d.line;
            lineInp.appendChild(opt);
        });
    }
});