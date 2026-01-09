

function handler(req) {

    /** @type {string | null} */
    const token = "token";  // Authenticate

    /** @type {string} */
    const accept = req.headers.get('accept') || '*/*';

    /** @type {Stream | null} */
    const stream = null

    if (accept === 'text/event-stream')
    {
        const maybeResponse = await onConnect?.(req);
        if (isResponse(maybeResponse)) return maybeResponse;

        // if event stream is not registered, process it directly.
        // this means that distinct connections are used for graphql operations
        if (!stream)
        {
            const paramsOrResponse = await parseReq(req);
            if (isResponse(paramsOrResponse)) return paramsOrResponse;
            const params = paramsOrResponse;

            const distinctStream = createStream(null);

            // reserve space for the operation
            distinctStream.ops[''] = null;

            const prepared = await prepare(req, params);
            if (isResponse(prepared)) return prepared;

            const result = await prepared.perform();
            if (isAsyncIterable(result)) distinctStream.ops[''] = result;

            distinctStream.from(prepared.ctx, req, result, null);
            return [
                distinctStream.subscribe(),
                {
                    status: 200,
                    statusText: 'OK',
                    headers: {
                        connection: 'keep-alive',
                        'cache-control': 'no-cache',
                        'content-encoding': 'none',
                        'content-type': 'text/event-stream; charset=utf-8',
                    },
                },
            ];
        }

        // open stream cant exist, only one per token is allowed
        if (stream.open)
        {
            return [
                JSON.stringify({errors: [{message: 'Stream already open'}]}),
                {
                    status: 409,
                    statusText: 'Conflict',
                    headers: {
                        'content-type': 'application/json; charset=utf-8',
                    },
                },
            ];
        }

        return [
            stream.subscribe(),
            {
                status: 200,
                statusText: 'OK',
                headers: {
                    connection: 'keep-alive',
                    'cache-control': 'no-cache',
                    'content-encoding': 'none',
                    'content-type': 'text/event-stream; charset=utf-8',
                },
            },
        ];
    }

    // if there is no token supplied, exclusively use the "distinct connection mode"
    if (typeof token !== 'string') {
        return [null, {status: 404, statusText: 'Not Found'}];
    }

    // method PUT prepares a stream for future incoming connections
    if (req.method === 'PUT')
    {
        if (!['*/*', 'text/plain'].includes(accept)) {
            return [null, {status: 406, statusText: 'Not Acceptable'}];
        }

        // streams mustnt exist if putting new one
        if (stream) {
            return [
                JSON.stringify({
                    errors: [{message: 'Stream already registered'}],
                }),
                {
                    status: 409,
                    statusText: 'Conflict',
                    headers: {
                        'content-type': 'application/json; charset=utf-8',
                    },
                },
            ];
        }

        streams[token] = createStream(token);

        return [
            token,
            {
                status: 201,
                statusText: 'Created',
                headers: {
                    'content-type': 'text/plain; charset=utf-8',
                },
            },
        ];
    } else if (req.method === 'DELETE')
    {
        // method DELETE completes an existing operation streaming in streams

        // streams must exist when completing operations
        if (!stream) {
            return [
                JSON.stringify({
                    errors: [{message: 'Stream not found'}],
                }),
                {
                    status: 404,
                    statusText: 'Not Found',
                    headers: {
                        'content-type': 'application/json; charset=utf-8',
                    },
                },
            ];
        }

        const opId = new URL(req.url ?? '', 'http://localhost/').searchParams.get(
          'operationId',
        );
        if (!opId) {
            return [
                JSON.stringify({
                    errors: [{message: 'Operation ID is missing'}],
                }),
                {
                    status: 400,
                    statusText: 'Bad Request',
                    headers: {
                        'content-type': 'application/json; charset=utf-8',
                    },
                },
            ];
        }

        const op = stream.ops[opId];
        if (isAsyncGenerator(op)) op.return(undefined);
        delete stream.ops[opId]; // deleting the operation means no further activity should take place

        return [
            null,
            {
                status: 200,
                statusText: 'OK',
            },
        ];
    } else if (req.method !== 'GET' && req.method !== 'POST')
    {
        // only POSTs and GETs are accepted at this point
        return [
            null,
            {
                status: 405,
                statusText: 'Method Not Allowed',
                headers: {
                    allow: 'GET, POST, PUT, DELETE',
                },
            },
        ];
    } else if (!stream)
    {
        // for all other requests, streams must exist to attach the result onto
        return [
            JSON.stringify({
                errors: [{message: 'Stream not found'}],
            }),
            {
                status: 404,
                statusText: 'Not Found',
                headers: {
                    'content-type': 'application/json; charset=utf-8',
                },
            },
        ];
    }

    if (!['*/*', 'application/*', 'application/json'].includes(accept)) {
        return [
            null,
            {
                status: 406,
                statusText: 'Not Acceptable',
            },
        ];
    }

    const paramsOrResponse = await parseReq(req);
    if (isResponse(paramsOrResponse)) return paramsOrResponse;
    const params = paramsOrResponse;

    const opId = String(params.extensions?.operationId ?? '');
    if (!opId) {
        return [
            JSON.stringify({
                errors: [{message: 'Operation ID is missing'}],
            }),
            {
                status: 400,
                statusText: 'Bad Request',
                headers: {
                    'content-type': 'application/json; charset=utf-8',
                },
            },
        ];
    }
    if (opId in stream.ops) {
        return [
            JSON.stringify({
                errors: [{message: 'Operation with ID already exists'}],
            }),
            {
                status: 409,
                statusText: 'Conflict',
                headers: {
                    'content-type': 'application/json; charset=utf-8',
                },
            },
        ];
    }

    // reserve space for the operation through ID
    stream.ops[opId] = null;

    const prepared = await prepare(req, params);
    if (isResponse(prepared)) return prepared;

    // operation might have completed before prepared
    if (!(opId in stream.ops)) {
        return [
            null,
            {
                status: 204,
                statusText: 'No Content',
            },
        ];
    }

    const result = await prepared.perform();

    // operation might have completed before performed
    if (!(opId in stream.ops)) {
        if (isAsyncGenerator(result)) result.return(undefined);
        if (!(opId in stream.ops)) {
            return [
                null,
                {
                    status: 204,
                    statusText: 'No Content',
                },
            ];
        }
    }

    if (isAsyncIterable(result)) stream.ops[opId] = result;

    // streaming to an empty reservation is ok (will be flushed on connect)
    stream.from(prepared.ctx, req, result, opId);

    return [null, {status: 202, statusText: 'Accepted'}];
}
