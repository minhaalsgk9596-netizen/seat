# -*- coding: utf-8 -*-
"""
자동 좌석배치 - 코드 배포 스크립트

하는 일
  1. 원본 HTML에 학생 데이터가 박혀 있지 않은지 확인 (개인정보 사고 방지 · 실패하면 즉시 중단)
  2. 버전 번호를 오늘 날짜로 올림 (원본 HTML + app.html 양쪽)
  3. 적어 준 메모를 [업데이트 내역] 창 맨 위에 추가
  4. app.html / version.json 갱신
  5. GitHub Pages로 push

쓰는 법: 상위 폴더의 [배포하기.bat] 더블클릭
        배포하기.bat 공석 표시 개선 ; 인쇄 여백 수정
        → 세미콜론(;)으로 나눈 만큼 업데이트 내역에 줄이 하나씩 생깁니다.
"""
import io, os, re, sys, json, shutil, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "자동 좌석배치 (원곡고Ver).html")
APP = os.path.join(HERE, "app.html")
VER = os.path.join(HERE, "version.json")

EMPTY_SLOT = "var EMBEDDED_DATA=null;/*@EMBED@*/"
VER_RE = re.compile(r'var APP_VERSION="[^"]*";/\*@VERSION@\*/')
CL_MARK = "/*@CHANGELOG@*/"


def die(msg):
    print("\n" + "!" * 60)
    print("중단: " + msg)
    print("!" * 60)
    sys.exit(1)


def run(*args):
    p = subprocess.run(args, cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        die("git 명령 실패: %s\n%s\n%s" % (" ".join(args), p.stdout or "", p.stderr or ""))
    return (p.stdout or "").strip()


def main():
    note = " ".join(sys.argv[1:]).strip()

    if not os.path.exists(SRC):
        die("원본 파일을 찾을 수 없습니다:\n  %s" % SRC)

    with io.open(SRC, encoding="utf-8", newline="") as f:
        s = f.read()

    # ---- 1. 개인정보 안전장치 -------------------------------------------
    if EMPTY_SLOT not in s:
        die("원본 HTML에 학생 데이터가 들어 있는 것 같습니다.\n"
            "   (%s 자리를 찾지 못했습니다)\n\n"
            "   배포용으로 저장된 파일을 원본에 덮어쓴 것은 아닌지 확인하세요.\n"
            "   학생 명단은 절대 인터넷에 올리면 안 되므로 배포를 멈춥니다." % EMPTY_SLOT)
    if not VER_RE.search(s):
        die("원본 HTML에서 APP_VERSION 줄을 찾지 못했습니다. 런처가 지워졌는지 확인하세요.")
    print("  [1/5] 개인정보 안전장치 통과 (학생 데이터 없음)")

    # ---- 2. 버전 올리기 --------------------------------------------------
    today = datetime.date.today().strftime("%Y.%m.%d")
    seq = 1
    if os.path.exists(VER):
        try:
            with io.open(VER, encoding="utf-8") as f:
                old = json.load(f).get("v", "")
            if old.startswith(today + "."):
                seq = int(old.rsplit(".", 1)[1]) + 1
        except Exception:
            pass
    new_ver = "%s.%d" % (today, seq)

    s = VER_RE.sub('var APP_VERSION="%s";/*@VERSION@*/' % new_ver, s, count=1)
    print("  [2/5] 버전 %s" % new_ver)

    # ---- 3. 업데이트 내역 추가 ------------------------------------------
    # 프로그램을 열면 뜨는 [업데이트 내역] 창에 이번 메모가 맨 위로 들어간다.
    if CL_MARK in s:
        items = [t.strip() for t in re.split(r"[;\n]", note) if t.strip()] or ["세부 기능 개선"]
        entry = '  {v:"%s", d:"%s", items:[%s]},' % (
            new_ver,
            datetime.date.today().strftime("%Y-%m-%d"),
            ", ".join(json.dumps(t, ensure_ascii=False) for t in items),
        )
        s = s.replace(CL_MARK, CL_MARK + "\n" + entry, 1)
        print("  [3/5] 업데이트 내역 %d줄 추가" % len(items))
        for t in items:
            print("        · %s" % t)
    else:
        print("  [3/5] 업데이트 내역 표시(%s)를 찾지 못해 건너뜁니다." % CL_MARK)

    with io.open(SRC, "w", encoding="utf-8", newline="") as f:
        f.write(s)

    # ---- 4. 배포 파일 쓰기 ----------------------------------------------
    shutil.copyfile(SRC, APP)
    payload = {
        "v": new_ver,
        "note": note or "기능 수정",
        "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with io.open(VER, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print("  [4/5] app.html (%.0fKB) · version.json 작성" % (os.path.getsize(APP) / 1024))

    # ---- 5. push ---------------------------------------------------------
    if not run("git", "remote"):
        print("  [5/5] GitHub 저장소가 아직 연결되지 않아 push를 건너뜁니다.")
        print("        (최초 1회) 저장소를 만든 뒤 아래를 실행하세요:")
        print('          cd "%s"' % HERE)
        print("          git remote add origin https://github.com/<계정>/seat.git")
    elif not run("git", "status", "--porcelain"):
        print("  [5/5] 바뀐 내용이 없어 push를 건너뜁니다.")
    else:
        run("git", "add", "-A")
        run("git", "commit", "-m", "v%s - %s" % (new_ver, payload["note"]))
        run("git", "push", "-u", "origin", "main")
        print("  [5/5] GitHub Pages로 push 완료")

    print("""
============================================================
 배포 완료 — 버전 %s
============================================================
 선생님들 파일에는 약 1분 뒤부터 반영됩니다.
 (파일을 열면 아래에 '새 버전이 준비되었습니다' 띠가 뜨고,
  새로고침하거나 다음에 다시 열면 자동으로 적용됩니다.
  적용된 뒤 처음 열 때 [업데이트 내역] 창으로 바뀐 내용이 안내됩니다)

 * 파일을 다시 보낼 필요는 없습니다.
 * 명렬표나 시험 시간표가 바뀐 경우에만
   [배포용 파일 저장]으로 새로 만들어 보내세요.
============================================================""" % new_ver)


if __name__ == "__main__":
    main()
