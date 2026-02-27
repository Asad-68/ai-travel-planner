import React, { createContext, useContext, useState, useEffect } from "react";
import { login as apiLogin, register as apiRegister } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);

    useEffect(() => {
        const storedToken = localStorage.getItem("wanderly_token");
        const storedUser = localStorage.getItem("wanderly_user");
        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(JSON.parse(storedUser));
        }
    }, []);

    const login = async (email, password) => {
        const data = await apiLogin(email, password);
        if (data.error) throw new Error(data.error);
        localStorage.setItem("wanderly_token", data.token);
        localStorage.setItem("wanderly_user", JSON.stringify(data.user));
        setToken(data.token);
        setUser(data.user);
        return data.user;
    };

    const register = async (name, email, password) => {
        const data = await apiRegister(name, email, password);
        if (data.error) throw new Error(data.error);
        localStorage.setItem("wanderly_token", data.token);
        localStorage.setItem("wanderly_user", JSON.stringify(data.user));
        setToken(data.token);
        setUser(data.user);
        return data.user;
    };

    const logout = () => {
        localStorage.removeItem("wanderly_token");
        localStorage.removeItem("wanderly_user");
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, token, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
