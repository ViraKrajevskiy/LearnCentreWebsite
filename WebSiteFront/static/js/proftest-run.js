(function() {
  var qs = window.PROFTEST.QUESTIONS;
  var qi = 0;
  var answers = [];
  var registerUrl = window.PROFTEST_REGISTER_URL || '/register/';

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }

  function selOpt(el) {
    var opts = document.querySelectorAll('.pt-o');
    opts.forEach(function(o) { o.classList.remove('sel'); });
    el.classList.add('sel');
  }

  function renderQuestion() {
    var q = qs[qi];
    document.getElementById('qLbl').textContent = q.q;
    document.getElementById('qPct').textContent = Math.round((qi / qs.length) * 100) + '%';
    document.getElementById('ptFill').style.width = (qi / qs.length) * 100 + '%';

    var html = q.o.map(function(opt, idx) {
      return '<div class="pt-o" data-idx="' + idx + '" onclick="window.proftestSelOpt(this)"><span>' + opt.text + '</span><div class="pt-radio"></div></div>';
    }).join('');
    document.getElementById('ptOpts').innerHTML = html;
  }

  function nextStep() {
    var sel = document.querySelector('.pt-o.sel');
    if (!sel) return;
    var idx = parseInt(sel.getAttribute('data-idx'), 10);
    answers[qi] = idx;

    if (qi < qs.length - 1) {
      qi++;
      renderQuestion();
      var btn = document.getElementById('ptNext');
      btn.textContent = qi === qs.length - 1 ? 'Узнать результат' : 'Далее →';
    } else {
      showResult();
    }
  }

  function showResult() {
    var scores = { ai_business: 0, design_content: 0, python_ml: 0, analytics: 0 };
    var keys = ['ai_business', 'design_content', 'python_ml', 'analytics'];
    for (var i = 0; i < qs.length; i++) {
      var opt = qs[i].o[answers[i]];
      if (opt && opt.scores) {
        for (var k = 0; k < 4; k++) {
          scores[keys[k]] += opt.scores[k];
        }
      }
    }
    var profile = window.PROFTEST.getResult(scores);
    var html = window.PROFTEST.buildResultHtml(profile, registerUrl);
    document.querySelector('.pt-r').innerHTML = '<div class="pt-result-wrap">' + html + '</div>';

    var saveToProfileBtn = document.getElementById('ptSaveToProfile');
    var saveMsg = document.getElementById('ptSaveMsg');
    if (saveToProfileBtn) {
      saveToProfileBtn.addEventListener('click', function() {
        var url = window.PROFTEST_SAVE_TO_PROFILE_URL || '/api/v1/proftest/save-to-profile/';
        var token = typeof localStorage !== 'undefined' && localStorage.getItem('access');
        if (!token) {
          if (saveMsg) { saveMsg.textContent = 'Войдите в аккаунт, чтобы сохранить результат.'; saveMsg.className = 'pt-save-msg pt-save-msg-err'; }
          return;
        }
        if (saveMsg) { saveMsg.textContent = 'Сохранение…'; saveMsg.className = 'pt-save-msg'; }
        saveToProfileBtn.disabled = true;
        fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/json'
          },
          body: JSON.stringify({ profile_id: profile.id, scores_json: scores }),
          credentials: 'same-origin'
        }).then(function(res) {
          return res.text().then(function(text) {
            var data = {};
            try { data = text ? JSON.parse(text) : {}; } catch (_) {}
            return { ok: res.ok, data: data };
          });
        }).then(function(r) {
          if (r.ok) {
            if (saveMsg) { saveMsg.textContent = r.data.message || 'Результат сохранён в ваш профиль.'; saveMsg.className = 'pt-save-msg pt-save-msg-ok'; }
            saveToProfileBtn.textContent = 'Сохранено';
          } else {
            if (saveMsg) { saveMsg.textContent = r.data.error || r.data.detail || 'Ошибка. Попробуйте позже.'; saveMsg.className = 'pt-save-msg pt-save-msg-err'; }
            saveToProfileBtn.disabled = false;
          }
        }).catch(function() {
          if (saveMsg) { saveMsg.textContent = 'Ошибка сети.'; saveMsg.className = 'pt-save-msg pt-save-msg-err'; }
          saveToProfileBtn.disabled = false;
        });
      });
    }

    var retry = document.getElementById('ptRetry');
    if (retry) {
      retry.addEventListener('click', function() {
        qi = 0;
        answers = [];
        document.querySelector('.pt-r').innerHTML = [
          '<div class="pt-prog-row"><span class="pt-q-lbl" id="qLbl"></span><span class="pt-q-pct" id="qPct"></span></div>',
          '<div class="pt-bar"><div class="pt-fill" id="ptFill"></div></div>',
          '<div class="pt-opts" id="ptOpts"></div>',
          '<div class="pt-foot"><button type="button" class="pt-btn" id="ptNext">Далее →</button></div>'
        ].join('');
        renderQuestion();
        document.getElementById('ptNext').addEventListener('click', nextStep);
      });
    }
  }

  window.proftestSelOpt = function(el) {
    selOpt(el);
  };

  document.addEventListener('DOMContentLoaded', function() {
    renderQuestion();
    document.getElementById('ptNext').addEventListener('click', nextStep);
  });
})();
