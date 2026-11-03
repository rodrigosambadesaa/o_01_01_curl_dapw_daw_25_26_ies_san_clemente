import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

import media_downloader as md


@pytest.mark.parametrize('url', [
    'https://x.com/person/status/1', 'https://twitter.com/person/status/2',
    'https://www.youtube.com/watch?v=ABC', 'https://youtu.be/ABC',
    'https://www.instagram.com/p/ABC', 'https://www.tiktok.com/@user/video/123',
    'https://www.reddit.com/r/test/comments/abc',
])
def test_allowed_public_posts(url):
    assert md.validate_url(url, md.POST_HOSTS) == url


@pytest.mark.parametrize('url', [
    'http://x.com/user/status/1', 'https://x.com.evil.org/watch',
    'https://evilx.com/', 'https://x.com@evil.org/',
    'https://127.0.0.1/', 'https://[::1]/', 'https://x.com:444/',
    'file:///etc/passwd', 'javascript:alert(1)', 'https://x.com/\nhello',
    'https://x.com:invalid/', 'https://localhost/',
])
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        md.validate_url(url, md.POST_HOSTS)


def test_domains_require_dot_boundary():
    assert md.trusted_host('video.twimg.com', md.MEDIA_HOSTS)
    assert not md.trusted_host('evil-twitter.com', md.MEDIA_HOSTS)
    assert not md.trusted_host('twitter.com.evil.test', md.MEDIA_HOSTS)


def test_mime_allowlist():
    assert md.mime_extension('video/mp4; charset=utf8') == '.mp4'
    assert md.mime_extension('audio/mpeg') == '.mp3'
    assert md.mime_extension('text/html') is None
    assert md.mime_extension('image/svg+xml') is None
    assert md.mime_extension('application/x-mpegurl') is None


def test_data_url_bounds():
    assert md.decoded_data_url('data:image/png;base64,YWJj', 3) == b'abc'
    with pytest.raises(ValueError):
        md.decoded_data_url('data:image/png;base64,YWJj', 2)
    with pytest.raises(ValueError):
        md.decoded_data_url('data:image/png;base64,!!', 50)


def test_embedded_bounds():
    assert md.embedded_bytes({'encoding':'base64', 'text':'YWI='}, 2) == b'ab'
    with pytest.raises(ValueError):
        md.embedded_bytes({'encoding':'base64','text':'YWI='}, 1)


def test_atomic_write_removes_partial_file(tmp_path):
    target = tmp_path / 'hello.bin'
    with pytest.raises(ValueError):
        md.save_bytes(target, [b'abc', b'def'], 4)
    assert not target.exists()
    assert not list(tmp_path.glob('.media-*'))
    md.save_bytes(target, [b'abc'], 4)
    assert target.read_bytes() == b'abc'


def test_har_embedded_multimedia_deduplicates(tmp_path, monkeypatch):
    entries = []
    for url, mime, data in [
        ('https://pbs.twimg.com/img', 'image/png', b'png'),
        ('https://video.twimg.com/vid', 'video/mp4', b'video'),
        ('https://video.twimg.com/vid', 'video/mp4', b'video'),
        ('https://x.com/style.css', 'text/css', b'css'),
    ]:
        entries.append({'request': {'url':url}, 'response': {'content':{
            'mimeType':mime,'encoding':'base64','text':base64.b64encode(data).decode()
        }}})
    har = tmp_path/'session.har'
    har.write_text(json.dumps({'log':{'entries':entries}}), encoding='utf-8')
    monkeypatch.setattr(md, 'fetch_media', lambda *a: pytest.fail('No network'))
    found, downloaded = md.download_har(har, tmp_path/'out', 1024, 20)
    assert (found,downloaded) == (2,2)
    assert (tmp_path/'out/har/recurso_0001.png').read_bytes() == b'png'
    assert (tmp_path/'out/har/recurso_0002.mp4').read_bytes() == b'video'


def test_har_limits(tmp_path):
    har = tmp_path/'big.har'
    har.write_bytes(b'x' * (md.MAX_HAR_BYTES+1))
    with pytest.raises(ValueError, match='20 MiB'):
        md.download_har(har, tmp_path/'out', 100, 20)


def test_har_never_uses_captured_cookies(tmp_path, monkeypatch):
    har=tmp_path/'session.har'
    har.write_text(json.dumps({'log':{'entries':[{'request':{
        'url':'https://video.twimg.com/sample.mp4',
        'headers':[{'name':'Cookie','value':'secret'}]
    },'response':{'content':{'mimeType':'video/mp4'}}}]}}))
    args=[]
    def safe_download(*incoming):
        args.append(incoming)
    monkeypatch.setattr(md,'fetch_media',safe_download)
    assert md.download_har(har,tmp_path/'out',1024,20)==(1,1)
    assert len(args)==1
    assert 'secret' not in repr(args)


class Response:
    status_code=200
    is_redirect=False
    headers={'Content-Type':'video/mp4', 'Content-Length':'4'}
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def raise_for_status(self): pass
    def iter_content(self,chunk_size): yield b'data'


class Session:
    def __init__(self): self.trust_env=True; self.arguments=None
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def get(self,*args,**kwargs):
        self.arguments=(args,kwargs)
        assert self.trust_env is False
        return Response()


def test_http_fetch_does_not_forward_auth_or_follow_redirects(tmp_path,monkeypatch):
    session=Session()
    monkeypatch.setattr(requests,'Session',lambda:session)
    md.fetch_media('https://video.twimg.com/sample.mp4',tmp_path/'test.mp4','video/mp4',50)
    assert (tmp_path/'test.mp4').read_bytes()==b'data'
    assert session.arguments[1]['allow_redirects'] is False
    assert not ({'cookies','headers'} & set(session.arguments[1]))


def test_http_fetch_rejects_wrong_content_type(tmp_path,monkeypatch):
    class Html(Response): headers={'Content-Type':'text/html'}
    monkeypatch.setattr(requests,'Session',lambda:SessionWithResponse(Html()))
    with pytest.raises(ValueError,match='MIME'):
        md.fetch_media('https://video.twimg.com/fake.mp4',tmp_path/'file.mp4','video/mp4',50)
    assert not (tmp_path/'file.mp4').exists()


class SessionWithResponse(Session):
    def __init__(self, response): super().__init__(); self.response=response
    def get(self,*args,**kwargs): return self.response


def test_backend_selection_and_safe_commands():
    url='https://x.com/user/status/1?text=$(touch%20X)'
    assert md.select_backends(url,'auto')==('gallery-dl','yt-dlp')
    assert md.select_backends('https://youtube.com/watch?v=1','auto')==('yt-dlp',)
    for backend in ('gallery-dl','yt-dlp'):
        command=md.backend_command(backend,url,Path('/tmp/media'),10000,4)
        assert command[0]==md.sys.executable
        assert url == command[-1]
        assert '--config-ignore' in command or '--ignore-config' in command
        assert '--max-filesize' in command or '--filesize-max' in command


def test_post_fallback_success(tmp_path,monkeypatch):
    calls=[]
    def fake_run(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(returncode=1 if command[2]=='gallery_dl' else 0)
    monkeypatch.setattr(md.subprocess,'run',fake_run)
    assert md.download_post('https://x.com/user/status/1',tmp_path,'auto',1024,5)==1
    assert len(calls)==2
    assert all(c[1]['shell'] is False and c[1]['timeout']==180 for c in calls)


def test_cli_rejects_unsafe_link(capsys):
    assert md.main(['--url','https://127.0.0.1/admin'])==1
    assert 'direcciones IP' in capsys.readouterr().err


def test_cli_requires_input(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        md.main([])