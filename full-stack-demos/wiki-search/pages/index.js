import React, { useState } from "react";

import Image from "next/image";
import { Inter } from "next/font/google";

import RiseLoader from "react-spinners/RiseLoader";

const inter = Inter({ subsets: ["latin"] });

const SearchResult = ({ title, text, link, distance, bg_color }) => {
  return (
    <div className={`${bg_color} rounded`}>
      <div className={`py-4 pl-3 lg:py-4`}>
        <div className="flex justify-between">
          <h2 className="mb-3 text-lg font-bold lg:text-2xl lg:font-extrabold tracking-tight text-gray-900">
            {title}
          </h2>

          <div>
            <span className="bg-blue-100 text-blue-800 text-xs font-medium me-2 px-2.5 py-0.5 rounded">
              {`Distance: ${distance.toFixed(3)}`}
            </span>
          </div>
        </div>

        <p className="mb-3 text-gray-500">{text}</p>
        <a
          href={link}
          className="inline-flex items-center font-medium text-blue-600 hover:text-blue-800"
        >
          Read Full Article
          <svg
            className="w-2.5 h-2.5 ms-2 rtl:rotate-180"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 6 10"
          >
            <path
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="m1 9 4-4-4-4"
            />
          </svg>
        </a>
      </div>
    </div>
  );
};

export default function Home() {
  const [query, setQuery] = useState("");

  const [loading, setLoading] = useState(false);

  const [searchResults, setSearchResults] = useState([]);

  const [searchTime, setSearchTime] = useState();

  const exampleQueries = [
    "evolution of artificial intelligence",
    "what runs on linux",
    "cultural impact of global cinema",
    "how do black holes form",
  ];

  const handleSubmit = async (event, query) => {
    event.preventDefault();
    _handleSubmit(query);
  };

  const _handleSubmit = async (query) => {
    setSearchResults([]);
    setLoading(true);

    try {
      var response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });
    } catch (error) {
      return;
    } finally {
      setLoading(false);
    }

    const data = await response.json();
    setSearchResults(data.results);
    setSearchTime(data.searchTime);
  };

  return (
    <main
      className={`flex min-h-screen flex-col items-center pb-24 pt-10 px-10 ${inter.className} lg:px-24`}
    >
      <div className="z-10 w-full  items-center justify-between text-lg lg:flex lg:self-start">
        <a href="/">
          <p className="fixed left-0 top-0 flex w-full justify-center border-b border-blue-400 bg-gradient-to-b from-blue-600 to-blue-300 pb-6 pt-8 backdrop-blur-2xl text-2xl font-bold lg:static lg:w-auto lg:rounded-xl lg:border lg:p-4 lg:text-xl text-gray-100">
            WikiSearch
          </p>
        </a>

        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-white via-white lg:static lg:h-auto lg:w-auto lg:bg-none">
          <a
            className="flex place-items-center gap-2 p-8 lg:pointer-events-auto lg:p-0"
            href="https://lantern.dev"
            target="_blank"
            rel="noopener noreferrer"
          >
            <p className="text-gray-500 font-normal">A Demo Built By</p>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 176 41"
              className="w-28 text-stone-800 hover:text-stone-500"
            >
              <g fill="currentColor" clipPath="url(#logo-text_svg__a)">
                <path d="M42.1 10.52v19.5h9.87V32H39.94V10.52h2.16ZM56.99 32H54.8l7.89-21.48h2.67L73.34 32h-2.25l-2.1-5.7h-9.9l-2.1 5.7Zm6.75-18.45-3.99 10.86h8.55l-4.02-10.86c-.09-.3-.24-.66-.27-.87-.03.18-.15.57-.27.87ZM79.686 32h-2.16V10.52h2.19l11.82 17.88V10.52h2.13V32h-2.13l-11.85-17.88V32Zm18.177-19.5v-1.98h15.39v1.98h-6.63V32h-2.16V12.5h-6.6ZM130.296 32h-12.87V10.52h12.84v1.98h-10.68v7.74h9.69v1.95h-9.69v7.83h10.71V32Zm7.746 0h-2.16V10.52h8.01c4.35 0 6.99 2.4 6.99 6.21 0 3.09-1.62 5.25-4.38 6l4.59 9.27h-2.4l-4.38-8.91h-6.27V32Zm0-19.53v8.67h5.91c2.97 0 4.71-1.62 4.71-4.35 0-2.79-1.83-4.32-4.77-4.32h-5.85ZM158.431 32h-2.16V10.52h2.19l11.82 17.88V10.52h2.13V32h-2.13l-11.85-17.88V32ZM9.71 11.337l13.694 3.475c.315.08.54.36.54.675l.018 13.388c0 .288.342.45.576.279l2.206-1.594a.704.704 0 0 0 .288-.558l-.01-6.887c-.008-4.358-3.042-8.157-7.409-9.264l-7.22-1.828a.733.733 0 0 0-.612.117l-2.197 1.593a.338.338 0 0 0 .126.604Z"></path>
                <path d="M20.955 22.266c0-3.034-2.125-5.681-5.16-6.455l-6.634-1.684-2.827-.72a.734.734 0 0 0-.612.117L2.93 15.55.32 17.44a.704.704 0 0 0-.288.558l.009 6.888c0 4.357 3.043 8.165 7.4 9.264l7.22 1.828a.733.733 0 0 0 .613-.117l2.79-2.026 2.611-1.89a.704.704 0 0 0 .289-.559V28.64l-.01-6.374Zm-3.07-2.386.009 7.428c0 .288-.28.495-.568.423L9.71 25.804a.709.709 0 0 1-.54-.675L9.16 17.7c0-.288.28-.495.568-.423l7.616 1.927c.316.08.54.36.54.675Zm-.55 13.775L3.651 30.189a.709.709 0 0 1-.54-.676l-.018-13.36c0-.288.279-.495.567-.423l2.026.513c.234.063.405.27.405.504v3.736c.009 4.349 3.043 8.157 7.41 9.264l3.996 1.018c.235.063.406.27.406.504v1.963c0 .288-.28.495-.568.423Z"></path>
              </g>
              <defs>
                <clipPath id="logo-text_svg__a">
                  <path fill="#fff" d="M0 0h175.33v41H0z"></path>
                </clipPath>
              </defs>
            </svg>
          </a>
        </div>
      </div>

      <div className="w-full max-w-3xl mt-32 mb-8 lg:mt-16">
        <form
          onSubmit={(event) => {
            handleSubmit(event, query);
          }}
        >
          <label
            htmlFor="default-search"
            className="mb-2 text-sm font-medium text-gray-900 sr-only"
          >
            Search
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none">
              <svg
                className="w-4 h-4 text-gray-500"
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 20 20"
              >
                <path
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="m19 19-4-4m0-7A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z"
                />
              </svg>
            </div>
            <input
              type="search"
              id="default-search"
              className="block w-full p-4 ps-10 text-sm text-gray-900 border border-gray-300 rounded-lg bg-gray-50 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Search across Wikipedia passages..."
              onChange={(event) => {
                setQuery(event.target.value);
              }}
              value={query}
              required
            />
            <button
              type="submit"
              disabled={loading}
              className={`text-white absolute end-2.5 bottom-2.5 bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-4 py-2
          ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              Search
            </button>
          </div>
        </form>

        {!loading && searchResults.length == 0 && (
          <>
            <div className="2 mx-auto md:w-2/3 px-4 py-4 mt-12 flex-col rounded shadow-sm border border-gray-300 bg-gray-100 text-gray-500 font-medium text-lg">
              <h2 className="text-xl">About</h2>
              <div className="mt-2 text-gray-400 font-normal text-base space-y-3">
                <p>
                  This is a demo of{" "}
                  <a
                    href="https://lantern.dev"
                    className="text-blue-500 hover:text-blue-700 hover:underline"
                  >
                    Lantern DB's
                  </a>{" "}
                  powerful vector search.
                </p>
                <p>
                  You can enter a search query above and search for semantically
                  similar passages from Wikipedia articles.
                </p>
                <p>
                  Lantern performs this search over{" "}
                  <a
                    href="https://txt.cohere.com/embedding-archives-wikipedia/"
                    className="text-blue-500 hover:text-blue-700 hover:underline"
                  >
                    embeddings provided by Cohere
                  </a>
                  .
                </p>
              </div>
            </div>

            <div className="2 mx-auto md:w-2/3 px-4 py-4 mt-12 flex flex-col rounded shadow-sm border border-gray-300 bg-gray-100 text-gray-500 font-medium text-lg">
              <h3 className="text-base text-center">Example Searches</h3>
              <div className="mt-4 mx-2 grid grid-cols-2 gap-4 font-normal text-base">
                {exampleQueries.map((query) => (
                  <p
                    className="text-blue-400 hover:text-blue-500 hover:underline cursor-pointer"
                    onClick={() => {
                      setQuery(query);
                      _handleSubmit(query);
                    }}
                  >
                    {query}
                  </p>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {loading && (
        <div className="flex mt-20 justify-center items-center">
          <RiseLoader color={"#60A5FA"} />
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="w-full mt-6">
          <div className="flex justify-between">
            <p className="text-md text-gray-400">Results</p>
            {searchTime !== undefined && (
              <div>
                <span className="bg-gray-100 text-gray-500 text-xs font-medium px-1 py-0.5 rounded">
                  {`${searchTime}ms`}
                </span>
              </div>
            )}
          </div>

          <hr className="mb-2 h-0.5 border-t-0 bg-neutral-100 opacity-100" />

          {searchResults.map((item, idx) => (
            <SearchResult
              title={item.title}
              text={item.text_content}
              link={item.url}
              distance={item.cos_dist}
              bg_color={idx % 2 == 0 ? "bg-white" : "bg-gray-50"}
            />
          ))}
        </div>
      )}
    </main>
  );
}
