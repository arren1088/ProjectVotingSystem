// 假設您有一個投票計數器或狀態來追蹤是否已經選擇了三個選項
let votesSelected = 0; // 用於追蹤已選擇的票數

// 更新投票狀態，並檢查是否達到三票
function updateVoteStatus() {
  if (votesSelected >= 3) {
    document.getElementById('confirmButton').disabled = false; // 啟用送出按鈕
  }
  else {
    document.getElementById('confirmButton').disabled = true; // 禁用送出按鈕
  }
}

// 當用戶選擇或取消投票選項時，更新投票狀態
function toggleVoteSelection() {
  // 更新 votesSelected 數值
  // 當選擇投票選項時，增加 votesSelected
  // 當取消選擇時，減少 votesSelected

  updateVoteStatus();
}

// 當確認按鈕被點擊時，提交投票
function submitVotes() {
  // 提交投票的邏輯
  alert('投票已送出!');
  // 這裡可以加入送出投票的 API 或表單提交邏輯
}