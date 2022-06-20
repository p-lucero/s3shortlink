'''Templating functionality for HTML files and such.'''
from string import Template

TEMPLATE_HTML = Template('''<!DOCTYPE html>
<html>
<head>
    <title>Redirecting...</title>
</head>
<body>
	<noscript>
		Your browser doesn't appear to support Javascript, click <a href=$destination>here</a> to be redirected.
	</noscript>
</body>
</html>
<script>
	function updateCounter(t){
		return function(){
			document.write(`Redirecting you to <a href=$destination>$destination</a> in ${t} seconds...`);
			if (t === 0) {
				window.location.replace("$destination");
			}
		}
	}
	for (let i = 0; i <= $timeout; i++) {
		setTimeout(updateCounter($timeout - i), i * 1000);
	}
</script>
''')


def get_redirect_page(destination, timeout=5):
    # We use `safe_substitute` here to avoid runtime KeyError with ${t}, which
    # should be substituted at JavaScript runtime rather than Python runtime.
    return TEMPLATE_HTML.safe_substitute({
        'destination': destination,
        'timeout': timeout
    })
