"use client";
import React, { useState } from "react";
import { Eye, EyeOff, ArrowRight, X } from "lucide-react";
import { createClient } from '../../../lib/supabase/client'
import { useRouter } from 'next/navigation'

const Auth = () => {
  // useStateでユーザーが入力したメールアドレスとパスワードをemailとpasswordに格納する
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [openModal, setOpenModal] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");

  const router = useRouter();
  const supabase = createClient();

  // サインイン関数
  const signIn = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setMessage(error.message);
      } else {
        setMessage("");
        router.push('/');
        router.refresh();
      }
    } catch (error) {
      setMessage('ログイン中にエラーが発生しました');
    }
  };

  // サインアップ関数
  const signUp = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });

      if (error) {
        setMessage(error.message);
      } else {
        setMessage('確認メールを送信しました。メールを確認してください。');
      }
    } catch (error) {
      setMessage('登録中にエラーが発生しました');
    }
  };

  // パスワードリセット関数
    const resetPassword = async (email: string) => {
        try {
        setLoading(true);
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
            redirectTo: `${window.location.origin}/auth/reset-password`,
        });

        if (error) {
            setMessage(error.message);
        } else {
            setMessage('パスワードリセットメールを送信しました');
            setOpenModal(false);
            setResetEmail("");
        }
        } catch (error) {
        setMessage('パスワードリセット中にエラーが発生しました');
        } finally {
        setLoading(false);
        }
    };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white px-5 font-sans">
      {/* Logo Section */}
      <div className="mb-9 text-center">
        {/* <img
        src="/bound.svg"
        alt="Bound Logo"
        className="w-28 h-auto transition-transform duration-300 hover:scale-105"
        /> */}
      </div>

      {/* Form Container */}
      <div className="w-full max-w-2xl flex flex-col items-center p-12 rounded-3xl bg-white shadow-2xl transition-all duration-300 hover:shadow-3xl">
        {/* Header */}
        <h1 className="text-3xl font-bold mb-3.5 text-center text-gray-900 leading-tight">
          {isLogin ? "おかえりなさい 👋" : "ようこそ、アカウントを登録します！"}
        </h1>
        <p className="text-base text-gray-600 mb-10 text-center leading-relaxed">
          {isLogin ? "アカウントにログインして続行" : "登録に必要な情報を教えてください。"}
        </p>

        {/* Error/Success Message */}
        {message && (
          <div className={`w-full mb-6 p-4 rounded-xl text-sm ${
            message.includes('確認メール') || message.includes('リセットメール') 
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {message}
          </div>
        )}

        {/* Sign Up Fields */}
        {!isLogin && (
          <>
            <div className="mb-6 w-full">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                あなたのメールアドレス
              </label>
              <input
                type="email"
                placeholder="ex.email@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white hover:shadow-sm"
              />
            </div>

            <div className="mb-6 w-full">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                パスワードを作成
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="パスワードを入力（6文字以上）"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 bg-gray-50 border border-gray-200 rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white hover:shadow-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-600 hover:text-gray-800"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>
          </>
        )}

        {/* Login Fields */}
        {isLogin && (
          <>
            <div className="mb-6 w-full">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                メールアドレス
              </label>
              <input
                type="email"
                placeholder="ex.email@domain.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white hover:shadow-sm"
              />
            </div>
            <div className="mb-6 w-full">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                パスワード
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="パスワードを入力"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 bg-gray-50 border border-gray-200 rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white hover:shadow-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-600 hover:text-gray-800"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div className="w-full text-right mb-6">
              <button
                onClick={() => setOpenModal(true)}
                className="text-blue-500 text-sm font-medium hover:text-blue-700 hover:underline transition-colors duration-200"
              >
                パスワードをお忘れですか？
              </button>
            </div>
          </>
        )}

        {/* Submit Button */}
        <button
          disabled={loading || !email || password.length < 6}
          onClick={async () => {
            setLoading(true);
            setMessage("");
            if (isLogin) {
              await signIn(email, password);
            } else {
              await signUp(email, password);
            }
            setLoading(false);
          }}
          className="w-full py-3.5 mt-4 mb-7 bg-orange-500 text-white font-semibold text-base rounded-xl shadow-lg transition-all duration-300 hover:bg-orange-600 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 active:shadow-md disabled:bg-orange-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <>
              {isLogin ? "ログイン" : "アカウント登録"}
              <ArrowRight size={20} />
            </>
          )}
        </button>

        {/* Toggle Login/Signup */}
        <p className="text-sm text-gray-600 text-center">
          {isLogin ? (
            <>
              アカウントをお持ちでない方は{" "}
              <button
                onClick={() => {
                  setIsLogin(false);
                  setMessage("");
                }}
                className="text-blue-500 font-medium hover:text-blue-700 hover:underline transition-colors duration-200"
              >
                新規登録
              </button>
            </>
          ) : (
            <>
              すでにアカウントをお持ちの方は{" "}
              <button
                onClick={() => {
                  setIsLogin(true);
                  setMessage("");
                }}
                className="text-blue-500 font-medium hover:text-blue-700 hover:underline transition-colors duration-200"
              >
                こちらからログイン
              </button>
            </>
          )}
        </p>
      </div>

      {/* Password Reset Modal */}
      {openModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl shadow-2xl p-11 w-full max-w-md mx-4">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-2xl font-semibold text-gray-900">
                パスワードのリセット
              </h2>
              <button
                onClick={() => {
                  setOpenModal(false);
                  setMessage("");
                }}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={24} />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-6">
              登録時のメールアドレスを入力してください。パスワードリセットのメールをお送りします。
            </p>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                メールアドレス
              </label>
              <input
                type="email"
                placeholder="ex.email@domain.com"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setOpenModal(false);
                  setMessage("");
                }}
                className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors duration-200"
              >
                キャンセル
              </button>
              <button
                onClick={() => resetPassword(resetEmail)}
                disabled={loading || !resetEmail}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  "送信"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Auth;