'''
form — an MCP server over stdio with one tool, ask, that asks the person for one word through an MCP
form and returns what came back: the drive's stand-in for a server of the person's that asks, so a
scenario can open a form the way a real server does, `elicitation/create` sent mid-call.

Methods
-------
    send :
        write one JSON-RPC message to the client.
    serve :
        answer the client until its input closes.
'''

from __future__ import annotations

import json
import sys



#the one field the form asks for, in the flat schema MCP forms allow...
ASKED = {'type': 'object', 'properties': {'word': {'type': 'string', 'title': 'Word'}},
         'required': ['word']}


def send(msg: dict) -> None:
    '''write one JSON-RPC message to the client, one line, flushed at once.'''
    sys.stdout.write(json.dumps(msg) + '\n')
    sys.stdout.flush()


def serve() -> int:
    '''
    answer the client until its input closes.

    Returns
    -------
    int
        0, always.

    Notes
    -----
    initialize is answered in the client's own protocol version with the tools capability, and
    tools/list with the one tool; a call of ask sends the form, as the request `form-<call id>`,
    and its call is answered once the form's response comes back, carrying that response. a
    notification, which has no id, gets no answer, and any other request an empty result.
    '''
    calls = {}
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, mid = msg.get('method'), msg.get('id')
        if method == 'initialize':
            send({'jsonrpc': '2.0', 'id': mid, 'result': {
                'protocolVersion': (msg.get('params') or {}).get('protocolVersion', '2025-06-18'),
                'capabilities': {'tools': {}}, 'serverInfo': {'name': 'form', 'version': '1'}}})
        elif method == 'tools/list':
            send({'jsonrpc': '2.0', 'id': mid, 'result': {'tools': [{
                'name': 'ask', 'description': 'Ask the person for one word through a form.',
                'inputSchema': {'type': 'object', 'properties': {}}}]}})
        elif method == 'tools/call':
            calls[f'form-{mid}'] = mid
            send({'jsonrpc': '2.0', 'id': f'form-{mid}', 'method': 'elicitation/create',
                  'params': {'message': 'Type one word.', 'requestedSchema': ASKED}})
        elif method is None and mid in calls:
            came = json.dumps(msg.get('result') or msg.get('error'))
            send({'jsonrpc': '2.0', 'id': calls.pop(mid), 'result': {'content': [
                {'type': 'text', 'text': f'the form came back: {came}'}]}})
        elif method is not None and mid is not None:
            send({'jsonrpc': '2.0', 'id': mid, 'result': {}})
    return 0


if __name__ == '__main__':
    sys.exit(serve())
