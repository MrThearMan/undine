# File Upload

In this section, we'll cover the everything necessary for adding support for file uploads
to your GraphQL schema using the [GraphQL multipart request specification]{:target="_blank"}
specification.

[GraphQL multipart request specification]: https://github.com/jaydenseric/graphql-multipart-request-spec

## Setup

Undine supports file uploads, but they disabled by default due to security reasons.
Specifically, since file uploads are sent using a `multipart/form-data` request, they may be sent without
a [CORS preflight request]{:target="_blank"} if the browser determines the requests meets the criteria for
a ["simple request"]{:target="_blank"}.

[CORS preflight request]: https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request
["simple request"]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS#simple_requests

Therefore, you should make sure CSRF protection is enabled on the GraphQL endpoint.
This can be done by making sure that the GraphQL view has the `@csrf_protect` decorator,
or that the `CsrfViewMiddleware` exists in your `MIDDLEWARE` setting (and the view is not using `@csrf_exempt`).

```python
MIDDLEWARE = [
    # ...
    "django.middleware.csrf.CsrfViewMiddleware",
    # ...
]
```

Then you can enable file uploads by adding the following to your settings:

```python
UNDINE = {
    "FILE_UPLOAD_ENABLED": True,
}
```

## Uploading files

Undine has two [Scalars](scalars.md) for uploading files: `File` for uploading general files,
and `Image` for uploading images. They correspond to Django's `FileField` and `ImageField` respectively.
The `Image` scalar performs additional validations on the uploaded image,
such as checking if the uploaded file is an image file.

> Like Django's `ImageField`, using the `Image` scalar requires the `Pillow` library to be installed.
> You can install it together with Undine using `pip install undine[image]`.

Now, let's suppose we have the following model:

```python
-8<- "file_uploads/models.py"
```

If we create a basic setup for creating a `Task`:

```python
-8<- "file_uploads/mutation_type.py"
```

Our GraphQL schema will have the following input object type:

```graphql
input TaskCreateMutation {
  name: String!
  image: Image!
}
```

Now the client can send a request that conforms to the [GraphQL multipart request specification]{:target="_blank"},
and Undine's GraphQL view will parse the request and slot the files into the correct locations in the input data.

[GraphQL multipart request specification]: https://github.com/jaydenseric/graphql-multipart-request-spec

/// details | Example request

```text
POST /graphql/ HTTP/1.1
Content-Type: multipart/form-data; boundary=--BoUnDaRyStRiNg
Content-Length: 490

--BoUnDaRyStRiNg
Content-Disposition: form-data; name="operations"

{"query": "mutation($input: TaskCreateMutation!) { createTask(input: $input) { pk } }", "variables": {"input": {"name": "Task", "image": null}}}
--BoUnDaRyStRiNg
Content-Disposition: form-data; name="map"

{"0": ["variables.input.image"]}
--BoUnDaRyStRiNg
Content-Disposition: form-data; name="0"; filename="image.png"

\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x01c```\x00\x00\x00\x04\x00\x01\xe4\x94\x84\x06\x00\x00\x00\x00IEND\xaeB`\x82
--BoUnDaRyStRiNg--
```

///

See the [Implementations]{:target="_blank"} section in the GraphQL multipart request specification
for client side libraries that support file uploads.

[Implementations]: https://github.com/jaydenseric/graphql-multipart-request-spec?tab=readme-ov-file#implementations
