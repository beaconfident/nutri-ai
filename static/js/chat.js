document.querySelectorAll(".bot").forEach(msg => {
  let text = msg.innerText;
  msg.innerText = "";
  let i = 0;
  let typing = setInterval(() => {
    msg.innerText += text[i];
    i++;
    if (i >= text.length) clearInterval(typing);
  }, 20);
});
