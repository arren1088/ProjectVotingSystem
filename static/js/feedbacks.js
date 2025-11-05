let feedbacks = [];

document.getElementById("add_feedback_btn").addEventListener("click", function () {
  const feedbackText = document.getElementById("feedback_text").value;
  const selectedGroupId = document.getElementById("group_id").value;
  const feedbackDate = document.getElementById("feedback_date").value;
  const feedbackTime = document.getElementById("feedback_time").value;

  if (feedbackText.trim() === "") {
    alert("請輸入回饋內容！");
    return;
  }
  if (feedbackDate === "" || feedbackTime === "") {
    alert("請選擇日期與時間！");
    return;
  }

  const feedback = {
    feedback: feedbackText,
    groupId: selectedGroupId,
    feedbackDate: feedbackDate,
    feedbackTime: feedbackTime
  };

  feedbacks.push(feedback);

  const feedbackList = document.getElementById("feedback_list");
  const feedbackItem = document.createElement("div");
  feedbackItem.innerHTML = `
    <strong>組別：</strong> ${groupMap[selectedGroupId]} <br>
    <strong>回饋內容：</strong> ${feedbackText} <br>
    <strong>日期：</strong> ${feedbackDate} <br>
    <strong>時間：</strong> ${feedbackTime} <br>
    <hr>
  `;
  feedbackList.appendChild(feedbackItem);

  document.getElementById("feedback_text").value = "";
  document.getElementById("feedback_date").value = "";
  document.getElementById("feedback_time").value = "";

  document.getElementById("submit_form").style.display = "block";
});

document.getElementById("skip_feedback_btn").addEventListener("click", function () {
  if (confirm("您尚未填寫回饋，是否直接跳過？")) {
    window.location.href = "/succeed";
  }
});

document.getElementById("submit_form").addEventListener("submit", function (event) {
  event.preventDefault();

  if (feedbacks.length === 0) {
    if (confirm("您尚未填寫回饋，是否直接提交？")) {
      window.location.href = "/succeed";
    }
    return;
  }

  const feedbackData = JSON.stringify(feedbacks);

  fetch("/api/feedback/batch", {
    method: "POST",
    body: new URLSearchParams({
      data: feedbackData
    }),
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      feedbacks = [];
      document.getElementById("feedback_list").innerHTML = "";
      document.getElementById("submit_form").style.display = "none";
      window.location.href = "/succeed";
    } else {
      alert("提交失敗：" + data.message);
    }
  })
  .catch(error => {
    alert("發生錯誤，請稍後再試！");
    console.error("Error:", error);
  });
});

flatpickr("#feedback_date", {
  dateFormat: "Y-m-d",
  maxDate: "today",
  locale: "zh_TW",
});

flatpickr("#feedback_time", {
  enableTime: true,
  noCalendar: true,
  dateFormat: "H:i",
  time_24hr: true,
});