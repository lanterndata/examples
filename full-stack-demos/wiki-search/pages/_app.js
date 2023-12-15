import "@/styles/globals.css";
import Head from "next/head";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>WikiSearch - Lantern Demo</title>
      </Head>
      <Component {...pageProps} />
    </>
  );
}
