Page through the list endpoints
================================

``GET /instance/``, ``GET /case/`` and ``GET /execution/`` return a page of rows, not the whole list: at most
``limit`` rows (10 by default), starting at ``offset`` (0 by default), newest first. The body is a plain JSON
list, so it does not say whether more rows exist. A client that needs every row has to page.

The response headers describe the page:

.. list-table::
   :header-rows: 1

   * - Header
     - Meaning
   * - ``X-Total-Count``
     - Number of rows that match the same filters and are visible to the user, ignoring ``offset`` and ``limit``.
   * - ``X-Offset`` / ``X-Limit``
     - The offset and page size that were applied.
   * - ``Link``
     - URL of the next and previous pages (``rel="next"`` / ``rel="prev"``), keeping the filters of the request.
       Absent when there is no such page.

The total follows the same rules as the list: a planner counts only their own rows, an admin counts every
visible row, and client users do not count the rows of platform users. The headers are listed in
``Access-Control-Expose-Headers``, so browsers can read them in cross-origin requests.

.. code-block:: python

    import requests

    rows, offset, limit = [], 0, 100
    while True:
        response = requests.get(
            f"{url}/execution/",
            params={"offset": offset, "limit": limit},
            headers={"Authorization": f"Bearer {token}"},
        )
        page = response.json()
        rows += page
        offset += limit
        if offset >= int(response.headers["X-Total-Count"]):
            break
